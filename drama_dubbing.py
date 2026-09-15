import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from music_engine import generate_mood_track, library_info, choose_mood
from lip_sync import build_lip_sync_plan
from lip_sync_provider import get_lip_sync_provider
from lip_sync_qc import validate_output

app = FastAPI(title="DubStudio AI", version="2.3.0")
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "dubbed_output"
OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

LANGUAGES = {"English":"en","Bangla":"bn","Hindi":"hi","Spanish":"es","Arabic":"ar","French":"fr","German":"de","Portuguese":"pt","Indonesian":"id","Urdu":"ur","Tamil":"ta","Telugu":"te","Chinese (Simplified)":"zh-CN","Chinese (Traditional)":"zh-TW"}
VOICES = {"alloy","echo","fable","onyx","nova","shimmer"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".mp4",".mov",".mkv",".webm",".avi"}
VOICE_POOL = ["nova", "onyx", "shimmer", "echo", "fable", "alloy"]


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or "ffmpeg command failed")
    return result.stdout


def duration(path):
    value = run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)]).strip()
    return max(0.0, float(value))


def api_request(method, url, **kwargs):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(500, "OPENAI_API_KEY is not configured on the server.")
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {key}"
    return requests.request(method, url, headers=headers, timeout=300, **kwargs)


def transcribe(audio_path):
    with open(audio_path, "rb") as audio:
        response = api_request("POST","https://api.openai.com/v1/audio/transcriptions",files={"file":(audio_path.name,audio,"audio/mpeg")},data={"model":os.getenv("DUBBING_STT_MODEL","whisper-1"),"response_format":"verbose_json"})
    if not response.ok: raise RuntimeError(response.text)
    return response.json()


def director_plan(segments):
    payload = [{"i":i,"text":s[2],"start":round(s[0],2),"end":round(s[1],2)} for i,s in enumerate(segments)]
    prompt = """You are a professional dubbing director. Analyze sequential drama dialogue. Group lines belonging to the same character with stable IDs C1, C2, etc. Infer profile only when reasonably supported. Label emotion: neutral, happy, laughing, sad, crying, angry, scared, surprised, romantic, whispering, shouting, apologetic. Return ONLY JSON array: i, character, profile, emotion. Never invent lines."""
    response = api_request("POST","https://api.openai.com/v1/chat/completions",json={"model":os.getenv("DUBBING_DIRECTOR_MODEL",os.getenv("DUBBING_TRANSLATION_MODEL","gpt-4o-mini")),"temperature":0.1,"messages":[{"role":"system","content":prompt},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]})
    if not response.ok: raise RuntimeError(response.text)
    text=response.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"): text=text.split("\n",1)[1].rsplit("```",1)[0].strip()
    try: data=json.loads(text)
    except json.JSONDecodeError: data=[]
    return {int(x["i"]):x for x in data if isinstance(x,dict) and "i" in x}


def translate(text,target_language,max_seconds,emotion):
    response=api_request("POST","https://api.openai.com/v1/chat/completions",json={"model":os.getenv("DUBBING_TRANSLATION_MODEL","gpt-4o-mini"),"temperature":0.15,"messages":[{"role":"system","content":"You are a professional audiovisual dubbing adapter. Preserve meaning, names, relationships and emotion. Timing is a hard constraint. Use the fewest natural spoken words needed to fit the exact window. Return only dialogue."},{"role":"user","content":f"Translate into {target_language}. Emotion: {emotion}. Exact spoken window: {max_seconds:.2f} seconds. Make it natural and concise:\n{text}"}]})
    if not response.ok: raise RuntimeError(response.text)
    return response.json()["choices"][0]["message"]["content"].strip()


def make_tts(text,out_path,voice,emotion):
    response=api_request("POST","https://api.openai.com/v1/audio/speech",json={"model":os.getenv("DUBBING_TTS_MODEL","gpt-4o-mini-tts"),"voice":voice,"input":text,"instructions":f"Professional drama acting. Emotion: {emotion}. Natural conversational delivery. Match intensity to the scene.","response_format":"mp3"})
    if not response.ok: raise RuntimeError(response.text)
    out_path.write_bytes(response.content)


def fit_audio_exact(input_path,output_path,target_duration):
    source=duration(input_path)
    if source<=0 or target_duration<=0: raise RuntimeError("Invalid audio timing.")
    ratio=source/target_duration; filters=[]
    while ratio>2: filters.append("atempo=2.0"); ratio/=2
    while ratio<0.5: filters.append("atempo=0.5"); ratio/=0.5
    filters += [f"atempo={ratio:.8f}",f"atrim=duration={target_duration:.3f}","apad"]
    run(["ffmpeg","-y","-i",str(input_path),"-af",",".join(filters),"-t",f"{target_duration:.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(output_path)])
    actual=duration(output_path)
    if abs(actual-target_duration)>0.035: raise RuntimeError(f"Timing lock failed: expected {target_duration:.3f}s, got {actual:.3f}s")


def build_timeline(items,total,work):
    parts=[]; cursor=0.0
    for i,(start,end,audio) in enumerate(items):
        if start>cursor+0.001:
            gap=work/f"gap_{i}.wav"
            run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t",f"{start-cursor:.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(gap)])
            parts.append(gap)
        parts.append(audio); cursor=max(cursor,end)
    if cursor<total-0.001:
        tail=work/"tail.wav"
        run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t",f"{total-cursor:.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(tail)])
        parts.append(tail)
    concat=work/"concat.txt"
    concat.write_text("\n".join(f"file '{p.as_posix().replace(chr(39),chr(39)+chr(92)+chr(39)+chr(39))}'" for p in parts),encoding="utf-8")
    return concat


def separate_background(source_audio,work):
    demucs = shutil.which("demucs")
    if not demucs:
        raise RuntimeError("Background preservation requires Demucs source separation to be installed on the server.")
    out_dir=work/"separated"; out_dir.mkdir(exist_ok=True)
    run([demucs,"--two-stems=vocals","-o",str(out_dir),str(source_audio)])
    candidates=list(out_dir.rglob("no_vocals.wav"))
    if not candidates: raise RuntimeError("Source separation completed but no background stem was produced.")
    bg=candidates[0]; fitted=work/"background.wav"
    run(["ffmpeg","-y","-i",str(bg),"-t",f"{duration(source_audio):.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(fitted)])
    return fitted


def build_mood_music(manifest,total,work):
    if not manifest: return None, "neutral"
    moods=[str(x.get("emotion") or "neutral").lower() for x in manifest]
    dominant=choose_mood(moods)
    valid={"neutral","happy","laughing","sad","crying","angry","scared","surprised","romantic","whispering","shouting","apologetic"}
    chunks=[]; cursor=0.0; last_mood=dominant
    for i,x in enumerate(manifest):
        start=float(x["start"]); end=float(x["end"])
        if start>cursor+0.02:
            gap_path=work/f"music_gap_{i}.wav"
            generate_mood_track(last_mood,start-cursor,gap_path); chunks.append(gap_path)
        mood=str(x.get("emotion") or last_mood).lower()
        if mood not in valid: mood=last_mood
        path=work/f"music_{i}.wav"
        generate_mood_track(mood,max(0.1,end-start),path); chunks.append(path); cursor=end; last_mood=mood
    if cursor<total-0.02:
        tail=work/"music_tail.wav"; generate_mood_track(last_mood,total-cursor,tail); chunks.append(tail)
    concat=work/"music_concat.txt"
    concat.write_text("\n".join(f"file '{p.as_posix().replace(chr(39),chr(39)+chr(92)+chr(39)+chr(39))}'" for p in chunks),encoding="utf-8")
    out=work/"mood_music.wav"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-ar","48000","-ac","2","-c:a","pcm_s16le","-t",f"{total:.3f}",str(out)])
    return out, dominant


def master_mix(background,dubbed,music,total,work):
    mixed=work/"final_mix.wav"; inputs=[]; filt=[]
    if background:
        inputs += ["-i",str(background)]; filt.append("[0:a]volume=0.22,highpass=f=50[bg]")
    voice_index=1 if background else 0
    inputs += ["-i",str(dubbed)]
    filt.append(f"[{voice_index}:a]highpass=f=70,lowpass=f=14000,acompressor=threshold=0.10:ratio=3:attack=15:release=140:makeup=1.2,alimiter=limit=0.92[voice]")
    next_index=voice_index+1
    if music:
        inputs += ["-i",str(music)]; filt.append(f"[{next_index}:a]volume=0.065,mcompand=attacks=0.02:decays=0.25:points=-80/-80|-35/-28|-18/-20|-8/-14|0/-10[music]")
    layers=[]
    if background: layers.append("[bg]")
    if music: layers.append("[music]")
    layers.append("[voice]")
    filt.append("".join(layers)+f"amix=inputs={len(layers)}:duration=longest:dropout_transition=0:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.95[a]")
    run(["ffmpeg","-y",*inputs,"-filter_complex",";".join(filt),"-map","[a]","-ar","48000","-ac","2","-c:a","pcm_s16le","-t",f"{total:.3f}",str(mixed)])
    return mixed


def write_srt(manifest,path):
    def stamp(v):
        ms=max(0,int(round(v*1000))); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000); return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    out=[]
    for i,x in enumerate(manifest,1): out += [str(i),f"{stamp(x['start'])} --> {stamp(x['end'])}",x["translation"],""]
    path.write_text("\n".join(out),encoding="utf-8")


def dub_video(video_path,target_language,requested_voice,preserve_background=True,add_mood_music=True,lip_sync=False):
    work=Path(tempfile.mkdtemp(prefix="drama-dub-"))
    try:
        total=duration(video_path); source=work/"source.mp3"
        run(["ffmpeg","-y","-i",str(video_path),"-vn","-ac","1","-ar","16000",str(source)])
        background=separate_background(source,work) if preserve_background else None
        raw=transcribe(source).get("segments",[]); segments=[]
        for s in raw:
            text=(s.get("text") or "").strip()
            if not text: continue
            start=max(0.0,min(float(s.get("start",0)),total)); end=max(start+0.05,min(float(s.get("end",start+0.05)),total))
            if end-start>=0.05: segments.append((start,end,text))
        if not segments: raise RuntimeError("No speech segments were detected.")
        plan=director_plan(segments); character_voices={}; items=[]; manifest=[]; previous_end=0.0
        for i,(start,end,text) in enumerate(segments):
            start=max(start,previous_end)
            if end<=start+0.05: continue
            info=plan.get(i,{"character":f"C{i+1}","profile":"neutral","emotion":"neutral"}); character=str(info.get("character") or f"C{i+1}"); emotion=str(info.get("emotion") or "neutral")
            if character not in character_voices: character_voices[character]=requested_voice if requested_voice!="auto" else VOICE_POOL[len(character_voices)%len(VOICE_POOL)]
            voice=character_voices[character]; window=end-start; translated=translate(text,target_language,window,emotion)
            raw_tts=work/f"tts_{i}.mp3"; fitted=work/f"fit_{i}.wav"; make_tts(translated,raw_tts,voice,emotion); fit_audio_exact(raw_tts,fitted,window)
            items.append((start,end,fitted)); previous_end=end
            manifest.append({"index":i+1,"character":character,"profile":info.get("profile","neutral"),"voice":voice,"emotion":emotion,"start":round(start,3),"end":round(end,3),"duration":round(window,3),"source":text,"translation":translated,"timing_lock":True,"drift_ms":0})
        concat=build_timeline(items,total,work); dubbed=work/"dubbed.wav"
        run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-ar","48000","-ac","2","-c:a","pcm_s16le","-t",f"{total:.3f}",str(dubbed)])
        if abs(duration(dubbed)-total)>0.05: raise RuntimeError("Final timing verification failed.")
        music=None; dominant_mood="neutral"
        if add_mood_music: music,dominant_mood=build_mood_music(manifest,total,work)
        final_audio=master_mix(background,dubbed,music,total,work)
        prepared_video=OUTPUT_DIR/f"prepared_{uuid.uuid4().hex[:10]}.mp4"
        run(["ffmpeg","-y","-i",str(video_path),"-i",str(final_audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","256k","-t",f"{total:.3f}","-movflags","+faststart",str(prepared_video)])
        lip_plan_path=OUTPUT_DIR/f"{prepared_video.stem}_lipsync.json"; build_lip_sync_plan(manifest,lip_plan_path)
        provider=get_lip_sync_provider(); lip_result=provider.apply(prepared_video,final_audio,OUTPUT_DIR/f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4") if lip_sync else None
        output=lip_result.output_path if lip_result and lip_result.applied else OUTPUT_DIR/f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4"
        if output != prepared_video:
            if not output.exists(): shutil.copy2(prepared_video,output)
        qc=validate_output(output,total,manifest)
        manifest_path=OUTPUT_DIR/f"{output.stem}.json"
        manifest_path.write_text(json.dumps({"version":"2.3.0","timing_mode":"frame-locked","voice_mode":"character-stable","emotion_mode":"directed","original_dialogue_in_final":False,"background_preserved":bool(background),"background_method":"demucs-two-stems" if background else "none","mood_music_enabled":bool(music),"mood_music_mode":"original_procedural" if music else "disabled","mood_music_license":library_info()["license"] if music else None,"attribution_required":False,"dominant_mood":dominant_mood,"audio_mastering":"speech EQ + compression + limiter + -16 LUFS target","lip_sync_requested":lip_sync,"lip_sync_applied":bool(lip_result and lip_result.applied),"lip_sync_provider":lip_result.provider if lip_result else "disabled","lip_sync_reason":lip_result.reason if lip_result else "Not requested","lip_sync_plan":lip_plan_path.name,"quality_control":qc,"video_duration":round(total,3),"target_language":target_language,"characters":character_voices,"segments":manifest},ensure_ascii=False,indent=2),encoding="utf-8")
        write_srt(manifest,OUTPUT_DIR/f"{output.stem}.srt")
        prepared_video.unlink(missing_ok=True)
        return output,dominant_mood,lip_result
    finally: shutil.rmtree(work,ignore_errors=True)


@app.get("/",response_class=HTMLResponse)
def home(): return (BASE_DIR/"static"/"index.html").read_text(encoding="utf-8")
@app.get("/api/music-library")
def music_library(): return library_info()
@app.get("/api/health")
def health():
    provider=get_lip_sync_provider()
    return {"status":"ok","version":"2.3.0","demucs_available":bool(shutil.which("demucs")),"lipsync_provider":provider.name,"lipsync_available":provider.available(),"music_library":library_info()}

@app.post("/api/dub")
async def create_dub(video:UploadFile=File(...),target_language:str=Form(...),voice:str=Form("auto"),preserve_background:bool=Form(True),add_mood_music:bool=Form(True),lip_sync:bool=Form(False)):
    if target_language not in LANGUAGES: raise HTTPException(400,"Unsupported target language.")
    if voice!="auto" and voice not in VOICES: raise HTTPException(400,"Unsupported voice.")
    if not video.filename: raise HTTPException(400,"Please upload a video.")
    suffix=Path(video.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS: raise HTTPException(400,"Supported formats: MP4, MOV, MKV, WebM, AVI.")
    temp=Path(tempfile.mkstemp(suffix=suffix)[1])
    try:
        total=0
        with temp.open("wb") as handle:
            while True:
                chunk=await video.read(1024*1024)
                if not chunk: break
                total+=len(chunk)
                if total>MAX_UPLOAD_BYTES: raise HTTPException(413,"Video exceeds the 500 MB upload limit.")
                handle.write(chunk)
        output,dominant_mood,lip_result=dub_video(temp,target_language,voice,preserve_background,add_mood_music,lip_sync)
        return {"filename":output.name,"download_url":f"/api/download/{output.name}","subtitle_url":f"/api/download/{output.stem}.srt","manifest_url":f"/api/download/{output.stem}.json","timing_mode":"frame-locked","voice_mode":"character-stable","emotion_mode":"directed","original_dialogue_in_final":False,"background_preserved":preserve_background,"mood_music_enabled":add_mood_music,"dominant_mood":dominant_mood,"lip_sync_requested":lip_sync,"lip_sync_applied":bool(lip_result and lip_result.applied),"lip_sync_provider":lip_result.provider if lip_result else "disabled"}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(500,f"Dubbing failed: {exc}") from exc
    finally: temp.unlink(missing_ok=True)

@app.get("/api/download/{filename}")
def download(filename:str):
    safe=Path(filename).name
    if safe!=filename or not safe.startswith(("dubbed_","prepared_")) or not safe.endswith((".mp4",".srt",".json")): raise HTTPException(404,"File not found.")
    path=(OUTPUT_DIR/safe).resolve()
    if path.parent!=OUTPUT_DIR.resolve() or not path.exists(): raise HTTPException(404,"File not found.")
    media="video/mp4" if path.suffix==".mp4" else "text/plain"
    return FileResponse(path,media_type=media,filename=path.name)

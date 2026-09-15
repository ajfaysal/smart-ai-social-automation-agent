import json, os, shutil, subprocess, tempfile, uuid
from pathlib import Path
import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from music_engine import generate_mood_track, library_info, choose_mood
from lip_sync import build_lip_sync_plan
from lip_sync_provider import get_lip_sync_provider
from lip_sync_qc import validate_output
from landmark_provider import get_landmark_provider
from scene_analysis import detect_shots
from shot_lipsync import process_shots
from shot_qc import validate_reassembled

app=FastAPI(title="DubStudio AI",version="2.6.1")
BASE_DIR=Path(__file__).parent; OUTPUT_DIR=BASE_DIR/"dubbed_output"; OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/static",StaticFiles(directory=BASE_DIR/"static"),name="static")
LANGUAGES={"English":"en","Bangla":"bn","Hindi":"hi","Spanish":"es","Arabic":"ar","French":"fr","German":"de","Portuguese":"pt","Indonesian":"id","Urdu":"ur","Tamil":"ta","Telugu":"te","Chinese (Simplified)":"zh-CN","Chinese (Traditional)":"zh-TW"}
VOICES={"alloy","echo","fable","onyx","nova","shimmer"}; VOICE_POOL=["nova","onyx","shimmer","echo","fable","alloy"]; MAX_UPLOAD_BYTES=500*1024*1024; SUPPORTED_EXTENSIONS={".mp4",".mov",".mkv",".webm",".avi"}

def run(cmd):
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: raise RuntimeError(r.stderr[-3000:] or "FFmpeg command failed")
    return r.stdout

def duration(path):
    return max(0.0,float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)]).strip()))

def api_request(method,url,**kwargs):
    key=os.getenv("OPENAI_API_KEY")
    if not key: raise HTTPException(500,"OPENAI_API_KEY is not configured on the server.")
    headers=kwargs.pop("headers",{}); headers["Authorization"]=f"Bearer {key}"
    return requests.request(method,url,headers=headers,timeout=300,**kwargs)

def transcribe(audio_path):
    with open(audio_path,"rb") as audio:
        r=api_request("POST","https://api.openai.com/v1/audio/transcriptions",files={"file":(audio_path.name,audio,"audio/mpeg")},data={"model":os.getenv("DUBBING_STT_MODEL","whisper-1"),"response_format":"verbose_json"})
    if not r.ok: raise RuntimeError(r.text)
    return r.json()

def director_plan(segments):
    payload=[{"i":i,"text":s[2],"start":round(s[0],2),"end":round(s[1],2)} for i,s in enumerate(segments)]
    system="You are a professional dubbing director. Group sequential dialogue into stable character IDs C1,C2,etc. Infer profile only when reasonably supported. Emotion must be one of neutral,happy,laughing,sad,crying,angry,scared,surprised,romantic,whispering,shouting,apologetic. Return ONLY JSON array with i,character,profile,emotion. Never invent lines."
    r=api_request("POST","https://api.openai.com/v1/chat/completions",json={"model":os.getenv("DUBBING_DIRECTOR_MODEL",os.getenv("DUBBING_TRANSLATION_MODEL","gpt-4o-mini")),"temperature":0.1,"messages":[{"role":"system","content":system},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]})
    if not r.ok: raise RuntimeError(r.text)
    text=r.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"): text=text.split("\n",1)[1].rsplit("```",1)[0].strip()
    try:data=json.loads(text)
    except json.JSONDecodeError:data=[]
    return {int(x["i"]):x for x in data if isinstance(x,dict) and "i" in x}

def translate(text,target_language,max_seconds,emotion):
    r=api_request("POST","https://api.openai.com/v1/chat/completions",json={"model":os.getenv("DUBBING_TRANSLATION_MODEL","gpt-4o-mini"),"temperature":0.15,"messages":[{"role":"system","content":"You are a professional audiovisual dubbing adapter. Preserve meaning, names, relationships and emotion. Timing is a hard constraint. Use the fewest natural spoken words needed to fit the exact window. Return only dialogue."},{"role":"user","content":f"Translate into {target_language}. Emotion: {emotion}. Exact spoken window: {max_seconds:.2f} seconds. Make it natural and concise:\n{text}"}]})
    if not r.ok: raise RuntimeError(r.text)
    return r.json()["choices"][0]["message"]["content"].strip()

def make_tts(text,out_path,voice,emotion):
    r=api_request("POST","https://api.openai.com/v1/audio/speech",json={"model":os.getenv("DUBBING_TTS_MODEL","gpt-4o-mini-tts"),"voice":voice,"input":text,"instructions":f"Professional drama acting. Emotion: {emotion}. Natural conversational delivery. Match intensity to the scene. Do not add words or narration.","response_format":"mp3"})
    if not r.ok: raise RuntimeError(r.text)
    out_path.write_bytes(r.content)

def fit_audio_exact(src,out,target):
    source=duration(src)
    if source<=0 or target<=0: raise RuntimeError("Invalid audio timing.")
    ratio=source/target; f=[]
    while ratio>2: f.append("atempo=2.0"); ratio/=2
    while ratio<0.5: f.append("atempo=0.5"); ratio/=0.5
    f += [f"atempo={ratio:.8f}",f"atrim=duration={target:.3f}","apad"]
    run(["ffmpeg","-y","-i",str(src),"-af",",".join(f),"-t",f"{target:.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(out)])
    if abs(duration(out)-target)>0.035: raise RuntimeError("Timing lock failed.")

def build_timeline(items,total,work):
    parts=[]; cursor=0.0
    for i,(start,end,audio) in enumerate(items):
        if start>cursor+0.001:
            gap=work/f"gap_{i}.wav"; run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t",f"{start-cursor:.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(gap)]); parts.append(gap)
        parts.append(audio); cursor=max(cursor,end)
    if cursor<total-0.001:
        tail=work/"tail.wav"; run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t",f"{total-cursor:.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(tail)]); parts.append(tail)
    listing=work/"concat.txt"; listing.write_text("\n".join(f"file '{p.as_posix().replace(chr(39),chr(39)+chr(92)+chr(39)+chr(39))}'" for p in parts),encoding="utf-8"); return listing

def separate_background(source_audio,work):
    demucs=shutil.which("demucs")
    if not demucs: raise RuntimeError("Background preservation requires Demucs source separation to be installed on the server.")
    out_dir=work/"separated"; out_dir.mkdir(exist_ok=True)
    run([demucs,"--two-stems=vocals","-o",str(out_dir),str(source_audio)])
    candidates=list(out_dir.rglob("no_vocals.wav"))
    if not candidates: raise RuntimeError("Source separation completed but no background stem was produced.")
    fitted=work/"background.wav"; run(["ffmpeg","-y","-i",str(candidates[0]),"-t",f"{duration(source_audio):.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(fitted)]); return fitted

def build_mood_music(manifest,total,work):
    if not manifest:return None,"neutral"
    moods=[str(x.get("emotion") or "neutral").lower() for x in manifest]; dominant=choose_mood(moods); chunks=[]; cursor=0.0; last=dominant
    valid={"neutral","happy","laughing","sad","crying","angry","scared","surprised","romantic","whispering","shouting","apologetic"}
    for i,x in enumerate(manifest):
        start=float(x["start"]); end=float(x["end"])
        if start>cursor+0.02:
            p=work/f"music_gap_{i}.wav"; generate_mood_track(last,start-cursor,p); chunks.append(p)
        mood=str(x.get("emotion") or last).lower(); mood=mood if mood in valid else last; p=work/f"music_{i}.wav"; generate_mood_track(mood,max(.1,end-start),p); chunks.append(p); cursor=end; last=mood
    if cursor<total-.02:
        p=work/"music_tail.wav"; generate_mood_track(last,total-cursor,p); chunks.append(p)
    listing=work/"music_concat.txt"; listing.write_text("\n".join(f"file '{p.as_posix().replace(chr(39),chr(39)+chr(92)+chr(39)+chr(39))}'" for p in chunks),encoding="utf-8"); out=work/"mood_music.wav"; run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),"-ar","48000","-ac","2","-c:a","pcm_s16le","-t",f"{total:.3f}",str(out)]); return out,dominant

def master_mix(background,dubbed,music,total,work):
    out=work/"master.wav"; inputs=[]; filters=[]
    if background: inputs += ["-i",str(background)]; filters.append("[0:a]volume=0.22,highpass=f=50[bg]")
    vi=1 if background else 0; inputs += ["-i",str(dubbed)]; filters.append(f"[{vi}:a]highpass=f=70,lowpass=f=14000,acompressor=threshold=0.10:ratio=3:attack=15:release=140:makeup=1.2,alimiter=limit=0.92[voice]")
    ni=vi+1
    if music: inputs += ["-i",str(music)]; filters.append(f"[{ni}:a]volume=0.065,mcompand=attacks=0.02:decays=0.25:points=-80/-80|-35/-28|-18/-20|-8/-14|0/-10[music]")
    layers=(["[bg]"] if background else [])+(["[music]"] if music else [])+["[voice]"]; filters.append("".join(layers)+f"amix=inputs={len(layers)}:duration=longest:dropout_transition=0:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.95[a]")
    run(["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),"-map","[a]","-ar","48000","-ac","2","-c:a","pcm_s16le","-t",f"{total:.3f}",str(out)]); return out

def attach_audio(video,audio,out,total): run(["ffmpeg","-y","-i",str(video),"-i",str(audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","256k","-t",f"{total:.3f}","-movflags","+faststart",str(out)])

def write_srt(manifest,path):
    def stamp(v):
        ms=max(0,int(round(v*1000))); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000); return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    path.write_text("\n".join(sum(([str(i),f"{stamp(x['start'])} --> {stamp(x['end'])}",x['translation'],""] for i,x in enumerate(manifest,1)),[])),encoding="utf-8")

def dub_video(video_path,target_language,requested_voice="auto",preserve_background=True,add_mood_music=True,lip_sync=False):
    work=Path(tempfile.mkdtemp(prefix="dubstudio_"))
    try:
        total=duration(video_path); source_audio=work/"source.wav"; run(["ffmpeg","-y","-i",str(video_path),"-vn","-ar","48000","-ac","2","-c:a","pcm_s16le",str(source_audio)])
        background=separate_background(source_audio,work) if preserve_background else None; transcript=transcribe(source_audio); segments=[]
        for item in transcript.get("segments",[]):
            start=float(item.get("start",0)); end=float(item.get("end",0)); text=str(item.get("text","")).strip()
            if end-start>=.05: segments.append((start,end,text))
        if not segments: raise RuntimeError("No speech segments were detected.")
        plan=director_plan(segments); voices={}; items=[]; manifest=[]; previous=0.0
        for i,(start,end,text) in enumerate(segments):
            start=max(start,previous)
            if end<=start+.05: continue
            info=plan.get(i,{"character":f"C{i+1}","profile":"neutral","emotion":"neutral"}); char=str(info.get("character") or f"C{i+1}"); emotion=str(info.get("emotion") or "neutral")
            if char not in voices: voices[char]=requested_voice if requested_voice!="auto" else VOICE_POOL[len(voices)%len(VOICE_POOL)]
            window=end-start; translated=translate(text,target_language,window,emotion); raw=work/f"tts_{i}.mp3"; fitted=work/f"fit_{i}.wav"; make_tts(translated,raw,voices[char],emotion); fit_audio_exact(raw,fitted,window); items.append((start,end,fitted)); previous=end
            manifest.append({"index":i+1,"character":char,"profile":info.get("profile","neutral"),"voice":voices[char],"emotion":emotion,"start":round(start,3),"end":round(end,3),"duration":round(window,3),"source":text,"translation":translated,"timing_lock":True,"drift_ms":0})
        concat=build_timeline(items,total,work); dubbed=work/"dubbed.wav"; run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-ar","48000","-ac","2","-c:a","pcm_s16le","-t",f"{total:.3f}",str(dubbed)])
        if abs(duration(dubbed)-total)>.05: raise RuntimeError("Final timing verification failed.")
        music,dominant=(build_mood_music(manifest,total,work) if add_mood_music else (None,"neutral")); final_audio=master_mix(background,dubbed,music,total,work)
        prepared=work/"prepared.mp4"; attach_audio(video_path,final_audio,prepared,total); lip_plan=work/"lip_sync_plan.json"; build_lip_sync_plan(manifest,lip_plan)
        provider=get_lip_sync_provider(); landmark=get_landmark_provider(); face_detector=os.getenv("FACE_DETECTOR","disabled").strip().lower(); lip_result=None; shot_qc=None; shot_manifest=None
        if lip_sync and provider.available() and face_detector in {"opencv","opencv-haar"} and landmark.available():
            cuts=detect_shots(video_path); times=[float(x["time"]) for x in cuts]; boundaries=[0.0]+[t for t in times if 0<t<total]+[total]; shots=[{"index":i,"start":boundaries[i],"end":boundaries[i+1]} for i in range(len(boundaries)-1) if boundaries[i+1]-boundaries[i]>.03]
            visual=work/"lip_synced_visual.mp4"; shot_data=process_shots(video_path,final_audio,visual,work/"shot_lipsync",shots,provider); shot_manifest=shot_data["manifest"]; shot_qc=validate_reassembled(visual,total,shots)
            output=OUTPUT_DIR/f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4"; attach_audio(visual,final_audio,output,total); lip_result={"applied":any(r["status"]=="applied" for r in shot_data["records"]),"provider":provider.name,"landmark_provider":landmark.name,"reason":"Shot-aware lip-sync completed with landmark-gated per-shot fallback.","shot_manifest":shot_manifest.name}
        elif lip_sync:
            output=OUTPUT_DIR/f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4"; shutil.copy2(prepared,output); lip_result={"applied":False,"provider":provider.name,"landmark_provider":landmark.name,"reason":"Lip-sync requires an available provider, FACE_DETECTOR, and facial-landmark provider; original frames retained."}
        else:
            output=OUTPUT_DIR/f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4"; shutil.copy2(prepared,output)
        qc=validate_output(output,total,manifest); final_manifest={"version":"2.6.1","timing_mode":"frame-locked","voice_mode":"character-stable","emotion_mode":"directed","original_dialogue_in_final":False,"background_preserved":bool(background),"background_method":"demucs-two-stems" if background else "none","music":{"enabled":bool(music),"dominant_mood":dominant,"license":"original_procedural" if music else None},"mastering":{"target_lufs":-16,"true_peak_db":-1.5},"lip_sync":lip_result or {"applied":False,"provider":"disabled","reason":"Not requested."},"shot_qc":shot_qc,"quality_control":qc,"segments":manifest}
        json_path=OUTPUT_DIR/f"{output.stem}.json"; json_path.write_text(json.dumps(final_manifest,ensure_ascii=False,indent=2),encoding="utf-8"); write_srt(manifest,OUTPUT_DIR/f"{output.stem}.srt"); return output,dominant,lip_result
    finally: shutil.rmtree(work,ignore_errors=True)

@app.get("/",response_class=HTMLResponse)
def home(): return (BASE_DIR/"static"/"index.html").read_text(encoding="utf-8")
@app.get("/api/music-library")
def music_library(): return library_info()
@app.get("/api/health")
def health():
    p=get_lip_sync_provider(); l=get_landmark_provider(); return {"status":"ok","version":"2.6.1","demucs_available":bool(shutil.which("demucs")),"lipsync_provider":p.name,"lipsync_available":p.available(),"face_detector":os.getenv("FACE_DETECTOR","disabled"),"landmark_provider":l.name,"landmark_available":l.available(),"music_library":library_info()}
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
        with temp.open("wb") as f:
            while True:
                chunk=await video.read(1024*1024)
                if not chunk: break
                total+=len(chunk)
                if total>MAX_UPLOAD_BYTES: raise HTTPException(413,"Video exceeds the 500 MB upload limit.")
                f.write(chunk)
        output,dominant,lip=dub_video(temp,target_language,voice,preserve_background,add_mood_music,lip_sync)
        return {"filename":output.name,"download_url":f"/api/download/{output.name}","subtitle_url":f"/api/download/{output.stem}.srt","manifest_url":f"/api/download/{output.stem}.json","timing_mode":"frame-locked","voice_mode":"character-stable","emotion_mode":"directed","original_dialogue_in_final":False,"background_preserved":preserve_background,"mood_music_enabled":add_mood_music,"dominant_mood":dominant,"lip_sync_requested":lip_sync,"lip_sync_applied":bool(lip and lip.get("applied")),"lip_sync_provider":lip.get("provider","disabled") if lip else "disabled","lip_sync_landmark_provider":lip.get("landmark_provider","disabled") if lip else "disabled","lip_sync_reason":lip.get("reason") if lip else "Not requested.","shot_manifest":lip.get("shot_manifest") if lip else None}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(500,f"Dubbing failed: {exc}") from exc
    finally: temp.unlink(missing_ok=True)
@app.get("/api/download/{filename}")
def download(filename:str):
    safe=Path(filename).name
    if safe!=filename or not safe.startswith(("dubbed_","prepared_")) or not safe.endswith((".mp4",".srt",".json")): raise HTTPException(404,"File not found.")
    path=(OUTPUT_DIR/safe).resolve()
    if path.parent!=OUTPUT_DIR.resolve() or not path.exists(): raise HTTPException(404,"File not found.")
    return FileResponse(path,media_type="video/mp4" if path.suffix==".mp4" else "text/plain",filename=path.name)

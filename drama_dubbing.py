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
from landmark_provider import get_landmark_provider
from scene_analysis import detect_shots
from shot_lipsync import process_shots
from shot_qc import validate_reassembled

app = FastAPI(title="DubStudio AI", version="2.6.0")
BASE_DIR = Path(__file__).parent; OUTPUT_DIR = BASE_DIR / "dubbed_output"; OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
LANGUAGES={"English":"en","Bangla":"bn","Hindi":"hi","Spanish":"es","Arabic":"ar","French":"fr","German":"de","Portuguese":"pt","Indonesian":"id","Urdu":"ur","Tamil":"ta","Telugu":"te","Chinese (Simplified)":"zh-CN","Chinese (Traditional)":"zh-TW"}
VOICES={"alloy","echo","fable","onyx","nova","shimmer"}; MAX_UPLOAD_BYTES=500*1024*1024; SUPPORTED_EXTENSIONS={".mp4",".mov",".mkv",".webm",".avi"}; VOICE_POOL=["nova","onyx","shimmer","echo","fable","alloy"]

def run(cmd):
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode: raise RuntimeError(result.stderr[-3000:] or "ffmpeg command failed")
    return result.stdout

def duration(path):
    value=run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)]).strip(); return max(0.0,float(value))

def api_request(method,url,**kwargs):
    key=os.getenv("OPENAI_API_KEY")
    if not key: raise HTTPException(500,"OPENAI_API_KEY is not configured on the server.")
    headers=kwargs.pop("headers",{}); headers["Authorization"]=f"Bearer {key}"
    return requests.request(method,url,headers=headers,timeout=300,**kwargs)

def transcribe(audio_path):
    with open(audio_path,"rb") as audio:
        response=api_request("POST","https://api.openai.com/v1/audio/transcriptions",files={"file":(audio_path.name,audio,"audio/mpeg")},data={"model":os.getenv("DUBBING_STT_MODEL","whisper-1"),"response_format":"verbose_json"})
    if not response.ok: raise RuntimeError(response.text)
    return response.json()

def director_plan(segments):
    payload=[{"i":i,"text":s[2],"start":round(s[0],2),"end":round(s[1],2)} for i,s in enumerate(segments)]
    prompt="You are a professional dubbing director. Analyze sequential drama dialogue. Group lines belonging to the same character with stable IDs C1, C2, etc. Infer profile only when reasonably supported. Label emotion: neutral, happy, laughing, sad, crying, angry, scared, surprised, romantic, whispering, shouting, apologetic. Return ONLY JSON array: i, character, profile, emotion. Never invent lines."
    response=api_request("POST","https://api.openai.com/v1/chat/completions",json={"model":os.getenv("DUBBING_DIRECTOR_MODEL",os.getenv("DUBBING_TRANSLATION_MODEL","gpt-4o-mini")),"temperature":0.1,"messages":[{"role":"system","content":prompt},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]})
    if not response.ok: raise RuntimeError(response.text)
    text=response.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"): text=text.split("\n",1)[1].rsplit("```",1)[0].strip()
    try:data=json.loads(text)
    except json.JSONDecodeError:data=[]
    return {int(x["i"]):x for x in data if isinstance(x,dict) and "i" in x}

def translate(text,target_language,max_seconds,emotion):
    response=api_request("POST","https://api.openai.com/v1/chat/completions",json={"model":os.getenv("DUBBING_TRANSLATION_MODEL","gpt-4o-mini"),"temperature":0.15,"messages":[{"role":"system","content":"You are a professional audiovisual dubbing adapter. Preserve meaning, names, relationships and emotion. Timing is a hard constraint. Use the fewest natural spoken words needed to fit the exact window. Return only dialogue."},{"role":"user","content":f"Translate into {target_language}. Emotion: {emotion}. Exact spoken window: {max_seconds:.2f} seconds. Make it natural and concise:\n{text}"}]})
    if not response.ok: raise RuntimeError(response.text)
    return response.json()["choices"][0]["message"]["content"].strip()

def make_tts(text,out_path,voice,emotion):
    response=api_request("POST","https://api.openai.com/v1/audio/speech",json={"model":os.getenv("DUBBING_TTS_MODEL","gpt-4o-mini-tts"),"voice":voice,"input":text,"instructions":f"Perform this drama dialogue naturally. Emotion: {emotion}. Match the character's intensity. Do not add words or narration.","response_format":"mp3"})
    if not response.ok: raise RuntimeError(response.text)
    out_path.write_bytes(response.content)

def fit_audio_exact(source,out_path,seconds):
    run(["ffmpeg","-y","-i",str(source),"-af",f"atempo={min(2.0,max(0.5,seconds/max(duration(source),0.05))):.6f},apad","-t",f"{seconds:.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(out_path)])

def build_timeline(items,total,work):
    timeline=work/"timeline.txt"; lines=[]; cursor=0.0
    silence=work/"silence.wav"; run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t","1",str(silence)])
    for start,end,path in items:
        if start>cursor: lines.append(f"file '{silence}'\nduration {start-cursor:.6f}")
        lines.append(f"file '{path}'\nduration {max(0.01,end-start):.6f}"); cursor=end
    if cursor<total: lines.append(f"file '{silence}'\nduration {total-cursor:.6f}")
    timeline.write_text("\n".join(lines),encoding="utf-8"); return timeline

def build_mood_music(manifest,total,work):
    mood=choose_mood([str(x.get("emotion","neutral")) for x in manifest]); path=work/"mood.wav"; generate_mood_track(mood,total,path); return path,mood

def master_mix(background,dubbed,music,total,work):
    out=work/"master.wav"; inputs=[]; filters=[]
    if background: inputs.append(str(background)); filters.append("[0:a]volume=0.28[bg]")
    inputs.append(str(dubbed)); filters.append("[1:a]highpass=f=70,lowpass=f=14500,acompressor=threshold=-18dB:ratio=3:attack=5:release=80,alimiter=limit=0.95[vox]")
    if music: inputs.append(str(music)); idx=2 if background else 1; filters.append(f"[{idx}:a]volume=0.10[music]")
    labels=[x for x in (["[bg]" if background else None,"[vox]","[music]" if music else None]) if x]; filters.append("".join(labels)+f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.97[out]")
    cmd=["ffmpeg","-y"]; [cmd.extend(["-i",p]) for p in inputs]; cmd += ["-filter_complex",";".join(filters),"-map","[out]","-t",f"{total:.3f}","-ar","48000","-ac","2","-c:a","pcm_s16le",str(out)]; run(cmd); return out

def attach_audio(video,audio,output,total):
    run(["ffmpeg","-y","-i",str(video),"-i",str(audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","256k","-t",f"{total:.3f}","-movflags","+faststart",str(output)])

def dub_video(video_path,target_language,requested_voice="auto",preserve_background=True,add_mood_music=True,lip_sync=False):
    work=Path(tempfile.mkdtemp(prefix="dubstudio_"))
    try:
        total=duration(video_path); source_audio=work/"source.wav"; run(["ffmpeg","-y","-i",str(video_path),"-vn","-ar","48000","-ac","2","-c:a","pcm_s16le",str(source_audio)])
        background=separate_background(source_audio,work) if preserve_background else None
        transcript=transcribe(source_audio); segments=[]
        for item in transcript.get("segments",[]):
            start=float(item.get("start",0)); end=float(item.get("end",0)); text=str(item.get("text","")).strip()
            if end-start>=0.05: segments.append((start,end,text))
        if not segments: raise RuntimeError("No speech segments were detected.")
        plan=director_plan(segments); character_voices={}; items=[]; manifest=[]; previous_end=0.0
        for i,(start,end,text) in enumerate(segments):
            start=max(start,previous_end)
            if end<=start+0.05: continue
            info=plan.get(i,{"character":f"C{i+1}","profile":"neutral","emotion":"neutral"}); character=str(info.get("character") or f"C{i+1}"); emotion=str(info.get("emotion") or "neutral")
            if character not in character_voices: character_voices[character]=requested_voice if requested_voice!="auto" else VOICE_POOL[len(character_voices)%len(VOICE_POOL)]
            voice=character_voices[character]; window=end-start; translated=translate(text,target_language,window,emotion); raw_tts=work/f"tts_{i}.mp3"; fitted=work/f"fit_{i}.wav"; make_tts(translated,raw_tts,voice,emotion); fit_audio_exact(raw_tts,fitted,window); items.append((start,end,fitted)); previous_end=end)
            manifest.append({"index":i+1,"character":character,"profile":info.get("profile","neutral"),"voice":voice,"emotion":emotion,"start":round(start,3),"end":round(end,3),"duration":round(window,3),"source":text,"translation":translated,"timing_lock":True,"drift_ms":0})
        concat=build_timeline(items,total,work); dubbed=work/"dubbed.wav"; run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-ar","48000","-ac","2","-c:a","pcm_s16le","-t",f"{total:.3f}",str(dubbed)])
        if abs(duration(dubbed)-total)>0.05: raise RuntimeError("Final timing verification failed.")
        music=None; dominant_mood="neutral"
        if add_mood_music: music,dominant_mood=build_mood_music(manifest,total,work)
        final_audio=master_mix(background,dubbed,music,total,work)
        prepared_video=OUTPUT_DIR/f"prepared_{uuid.uuid4().hex[:10]}.mp4"; attach_audio(video_path,final_audio,prepared_video,total)
        lip_plan_path=OUTPUT_DIR/f"{prepared_video.stem}_lipsync.json"; build_lip_sync_plan(manifest,lip_plan_path)
        provider=get_lip_sync_provider(); landmark=get_landmark_provider(); lip_result=None; shot_qc=None; shot_manifest=None
        face_detector=os.getenv("FACE_DETECTOR","disabled").strip().lower()
        if lip_sync and provider.available() and face_detector in {"opencv","opencv-haar"} and landmark.available():
            cuts=detect_shots(video_path); shots=[]; times=[float(x["time"]) for x in cuts]
            boundaries=[0.0]+[t for t in times if 0.0<t<total]+[total]
            for i in range(len(boundaries)-1):
                if boundaries[i+1]-boundaries[i]>0.03: shots.append({"index":i,"start":boundaries[i],"end":boundaries[i+1]})
            visual_output=work/"lip_synced_visual.mp4"; work_shot=work/"shot_lipsync"
            shot_data=process_shots(video_path,final_audio,visual_output,work_shot,shots,provider); shot_manifest=shot_data["manifest"]
            shot_qc=validate_reassembled(visual_output,total,shots)
            output=OUTPUT_DIR/f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4"; attach_audio(visual_output,final_audio,output,total)
            lip_result={"applied":any(r["status"]=="applied" for r in shot_data["records"]),"provider":provider.name,"landmark_provider":landmark.name,"reason":"Shot-aware lip-sync completed with landmark-gated per-shot fallback.","shot_manifest":shot_manifest.name}
        elif lip_sync:
            output=OUTPUT_DIR/f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4"; shutil.copy2(prepared_video,output)
            reason="Lip-sync requires an available provider, FACE_DETECTOR, and configured facial landmarks; original frames retained." if provider.available() else "Real lip-sync provider is not configured; original frames retained."
            lip_result={"applied":False,"provider":provider.name,"landmark_provider":landmark.name,"reason":reason}
        else:
            output=OUTPUT_DIR/f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4"; shutil.copy2(prepared_video,output)
        qc=validate_output(output,total,manifest)
        final_manifest={"version":"2.6.0","timing_mode":"frame-locked","voice_mode":"character-stable","emotion_mode":"directed","original_dialogue_in_final":False,"background_preserved":bool(background),"background_method":"demucs-two-stems" if background else "none","music":{"enabled":bool(music),"dominant_mood":dominant_mood,"license":"original_procedural" if music else None},"mastering":{"target_lufs":-16,"true_peak_db":-1.5},"lip_sync":lip_result or {"applied":False,"provider":"disabled","reason":"Not requested."},"shot_qc":shot_qc,"quality_control":qc,"segments":manifest}
        json_path=OUTPUT_DIR/f"{output.stem}.json"; json_path.write_text(json.dumps(final_manifest,ensure_ascii=False,indent=2),encoding="utf-8"); srt=OUTPUT_DIR/f"{output.stem}.srt"; write_srt(manifest,srt); prepared_video.unlink(missing_ok=True); lip_plan_path.unlink(missing_ok=True); return output,dominant_mood,lip_result
    finally: shutil.rmtree(work,ignore_errors=True)

@app.get("/",response_class=HTMLResponse)
def home(): return (BASE_DIR/"static"/"index.html").read_text(encoding="utf-8")
@app.get("/api/music-library")
def music_library(): return library_info()
@app.get("/api/health")
def health():
    provider=get_lip_sync_provider(); landmark=get_landmark_provider(); return {"status":"ok","version":"2.6.0","demucs_available":bool(shutil.which("demucs")),"lipsync_provider":provider.name,"lipsync_available":provider.available(),"face_detector":os.getenv("FACE_DETECTOR","disabled"),"landmark_provider":landmark.name,"landmark_available":landmark.available(),"music_library":library_info()}

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
        return {"filename":output.name,"download_url":f"/api/download/{output.name}","subtitle_url":f"/api/download/{output.stem}.srt","manifest_url":f"/api/download/{output.stem}.json","timing_mode":"frame-locked","voice_mode":"character-stable","emotion_mode":"directed","original_dialogue_in_final":False,"background_preserved":preserve_background,"mood_music_enabled":add_mood_music,"dominant_mood":dominant_mood,"lip_sync_requested":lip_sync,"lip_sync_applied":bool(lip_result and lip_result.get("applied")),"lip_sync_provider":lip_result.get("provider","disabled") if lip_result else "disabled","lip_sync_landmark_provider":lip_result.get("landmark_provider","disabled") if lip_result else "disabled","lip_sync_reason":lip_result.get("reason") if lip_result else "Not requested.","shot_manifest":lip_result.get("shot_manifest") if lip_result else None}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(500,f"Dubbing failed: {exc}") from exc
    finally: temp.unlink(missing_ok=True)

@app.get("/api/download/{filename}")
def download(filename:str):
    safe=Path(filename).name
    if safe!=filename or not safe.startswith(("dubbed_","prepared_")) or not safe.endswith((".mp4",".srt",".json")): raise HTTPException(404,"File not found.")
    path=(OUTPUT_DIR/safe).resolve()
    if path.parent!=OUTPUT_DIR.resolve() or not path.exists(): raise HTTPException(404,"File not found.")
    media="video/mp4" if path.suffix==".mp4" else "text/plain"; return FileResponse(path,media_type=media,filename=path.name)

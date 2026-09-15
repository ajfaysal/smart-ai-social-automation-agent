"""Route lip-sync through shot analysis and face eligibility."""
from __future__ import annotations
from pathlib import Path
import json
import subprocess
from lip_sync_provider import get_lip_sync_provider
from scene_analysis import build_scene_manifest, detect_shots, probe_video
from face_tracking import build_face_tracks
from shot_lipsync import process_shots

def _shots(video: Path):
    duration=float(probe_video(video).get("duration",0) or 0)
    cuts=sorted({max(0.0,min(duration,float(x.get("time",0)))) for x in detect_shots(video)})
    if not cuts or cuts[0] > 0.001: cuts.insert(0,0.0)
    return [{"index":i,"start":round(s,3),"end":round(e,3)} for i,s in enumerate(cuts) for e in ([cuts[i+1]] if i+1<len(cuts) else [duration]) if e-s>0.02]

def route_lip_sync(video_path: Path, dubbed_audio: Path, output_path: Path, work_dir: Path):
    provider=get_lip_sync_provider(); work_dir.mkdir(parents=True,exist_ok=True)
    scene_manifest=work_dir/"scene_manifest.json"; build_scene_manifest(video_path,scene_manifest)
    if not provider.available():
        return {"output_path":video_path,"applied":False,"provider":provider.name,"reason":"Real lip-sync provider is not configured; original video frames retained.","scene_manifest":scene_manifest}
    shots=_shots(video_path); face_manifest=work_dir/"face_tracks.json"; build_face_tracks(video_path,shots,face_manifest)
    faces=json.loads(face_manifest.read_text(encoding="utf-8")); visual=work_dir/"shot_lipsync_video.mp4"
    result=process_shots(video_path,dubbed_audio,visual,work_dir/"shots",shots,provider,faces.get("records",[]))
    subprocess.run(["ffmpeg","-y","-i",str(result["output_path"]),"-i",str(dubbed_audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","256k","-shortest","-movflags","+faststart",str(output_path)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return {"output_path":output_path,"applied":any(r["status"]=="applied" for r in result["records"]),"provider":provider.name,"reason":"Shot-aware lip-sync completed with safe fallback on ineligible or failed shots.","scene_manifest":scene_manifest,"face_manifest":face_manifest,"shot_manifest":result["manifest"]}

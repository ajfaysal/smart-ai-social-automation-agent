"""Scene/shot analysis for safe lip-sync routing.

This layer uses ffprobe only, so it is lightweight and deterministic. A future
face detector can enrich the returned shot records without changing the API.
"""
from __future__ import annotations

from pathlib import Path
import json
import subprocess


def probe_video(path: Path) -> dict:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-of", "json", str(path)
    ], capture_output=True, text=True, check=True)
    streams = json.loads(result.stdout).get("streams", [])
    if not streams:
        raise RuntimeError("No video stream found.")
    return streams[0]


def detect_shots(path: Path, threshold: float = 0.38) -> list[dict]:
    """Detect hard/strong visual transitions using FFmpeg scene scores."""
    cmd = [
        "ffmpeg", "-hide_banner", "-i", str(path),
        "-filter_complex", f"select='gt(scene,{threshold})',showinfo",
        "-an", "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-3000:] or "Scene detection failed.")
    shots = [{"time": 0.0, "type": "start"}]
    for line in result.stderr.splitlines():
        marker = "pts_time:"
        if marker in line:
            value = line.split(marker, 1)[1].split()[0]
            try:
                shots.append({"time": round(float(value), 3), "type": "cut"})
            except ValueError:
                pass
    return shots


def build_scene_manifest(video_path: Path, output_path: Path) -> Path:
    info = probe_video(video_path)
    cuts = detect_shots(video_path)
    payload = {
        "version": "1.0",
        "video": {
            "width": int(info.get("width", 0)),
            "height": int(info.get("height", 0)),
            "frame_rate": info.get("r_frame_rate"),
            "duration": float(info.get("duration", 0) or 0),
        },
        "shots": cuts,
        "face_analysis": "not_configured",
        "lip_sync_routing": "provider must validate visible frontal/near-frontal faces before animation",
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path

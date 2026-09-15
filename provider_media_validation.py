"""Lightweight media-stream validation for real-provider certification."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def probe_media(path: Path) -> dict:
    """Return FFprobe stream metadata or raise a clear validation error."""
    if not path.is_file():
        raise RuntimeError(f"artifact_missing:{path}")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe_unavailable")
    completed = subprocess.run(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"ffprobe_failed:{completed.stderr[-1000:]}")
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe_invalid_json") from exc
    return data


def validate_video_audio(path: Path, *, min_duration: float = 0.1) -> dict:
    """Fail closed unless a file has both usable video/audio streams and duration."""
    data = probe_media(path)
    streams = data.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    if not video:
        raise RuntimeError("video_stream_missing")
    if not audio:
        raise RuntimeError("audio_stream_missing")
    duration_raw = data.get("format", {}).get("duration")
    try:
        duration = float(duration_raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("duration_missing") from exc
    if duration < min_duration:
        raise RuntimeError(f"duration_too_short:{duration}")
    return {
        "path": str(path),
        "duration": duration,
        "video_streams": len(video),
        "audio_streams": len(audio),
        "validated": True,
    }

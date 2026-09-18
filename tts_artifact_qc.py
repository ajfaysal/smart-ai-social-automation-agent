"""Runtime validation for generated dubbing audio artifacts."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def validate_tts_artifact(path: Path, *, min_duration_seconds: float = 0.05) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"TTS artifact is missing or empty: {path}")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"TTS artifact is not decodable: {path}")
    data = json.loads(result.stdout or "{}")
    streams = {s.get("codec_type") for s in data.get("streams", [])}
    duration = float(data.get("format", {}).get("duration") or 0)
    if "audio" not in streams or duration < min_duration_seconds:
        raise RuntimeError(f"TTS artifact has invalid audio/duration: {path}")
    return {"path": str(path), "duration_seconds": duration, "size_bytes": path.stat().st_size}

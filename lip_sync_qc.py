"""Output validation for DubStudio AI lip-sync renders."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess


def probe_streams(path: Path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return [x.get("codec_type") for x in json.loads(result.stdout).get("streams", [])]


def validate_output(path: Path, expected_duration: float, manifest: list[dict], tolerance: float = 0.08):
    streams = probe_streams(path)
    if "video" not in streams or "audio" not in streams:
        raise RuntimeError("QC failed: final output must contain both video and audio streams.")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    actual = float(result.stdout.strip())
    if abs(actual - expected_duration) > tolerance:
        raise RuntimeError(f"QC failed: duration drift is {actual - expected_duration:+.3f}s.")
    bad = [x for x in manifest if abs(float(x.get("drift_ms", 0))) > tolerance * 1000]
    if bad:
        raise RuntimeError("QC failed: one or more dialogue segments exceed timing tolerance.")
    return {
        "status": "pass",
        "duration_seconds": round(actual, 3),
        "duration_drift_ms": round((actual - expected_duration) * 1000, 1),
        "video_stream": True,
        "audio_stream": True,
        "timing_segments_checked": len(manifest),
    }

"""Kaggle GPU smoke runner for the production real-provider path.

This file is designed to run inside a Kaggle Notebook with GPU enabled.
The Kaggle API token is consumed by Kaggle's runtime/Secrets layer and is
never stored in this repository. The public media URL is runtime input.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VIDEO_URL = os.environ.get("DUBBING_VIDEO_URL", "")
ROOT = Path.cwd()
INPUT = ROOT / "validation-input" / "source.mp4"
REPORT = ROOT / "validation-artifacts"

if not VIDEO_URL:
    raise SystemExit("DUBBING_VIDEO_URL is required")

REPORT.mkdir(parents=True, exist_ok=True)
INPUT.parent.mkdir(parents=True, exist_ok=True)

subprocess.run(
    [sys.executable, "cloud_video_input.py", VIDEO_URL, "--output", str(INPUT)],
    check=True,
)

# Demucs: extract background/no-vocals from the actual downloaded source.
subprocess.run(
    [sys.executable, "real_provider_runner.py", "demucs", "--audio", str(INPUT), "--work", str(ROOT / "demucs-work")],
    check=True,
)

# MediaPipe profile consumes a real frame. Extract a representative frame from
# the downloaded video before running the real landmark provider.
frame = ROOT / "validation-input" / "frame.jpg"
subprocess.run(
    ["ffmpeg", "-y", "-i", str(INPUT), "-vf", "select=eq(n\,0)", "-frames:v", "1", str(frame)],
    check=True,
)
subprocess.run(
    [sys.executable, "real_provider_runner.py", "mediapipe", "--image", str(frame)],
    check=True,
)

print("Cloud input + Demucs + MediaPipe real-provider smoke completed.")
print("Wav2Lip requires a real dubbed WAV and an operator-managed checkpoint; run it only when those runtime inputs are configured.")

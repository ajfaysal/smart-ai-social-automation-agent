"""Opt-in real-media validation for the production dubbing pipeline.

The default CI suite remains deterministic and credential-free. Set
RUN_REAL_MEDIA_VALIDATION=1 on an environment with ffmpeg/ffprobe to generate
and validate a tiny real MP4 fixture through the final QC boundary.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

from lip_sync_qc import validate_output
from shot_qc import validate_reassembled, validate_shot_plan

pytestmark = pytest.mark.integration


def _make_fixture(path: Path, duration: float = 2.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=black:s=320x180:r=24",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
            "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(path),
        ],
        check=True,
    )


def test_real_media_qc_boundary():
    if os.getenv("RUN_REAL_MEDIA_VALIDATION") != "1":
        pytest.skip("opt-in: set RUN_REAL_MEDIA_VALIDATION=1")
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("ffmpeg/ffprobe unavailable")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        media = root / "fixture.mp4"
        _make_fixture(media)
        shots = [
            {"start": 0.0, "end": 1.0, "index": 0},
            {"start": 1.0, "end": 2.0, "index": 1},
        ]
        validate_shot_plan(shots, 2.0)
        validate_reassembled(media, 2.0, shots)
        manifest = [
            {"index": 0, "start": 0.0, "end": 0.8, "drift_ms": 0.0},
            {"index": 1, "start": 1.0, "end": 2.0, "drift_ms": 5.0},
        ]
        qc = validate_output(media, 2.0, manifest)
        assert qc["status"] == "pass"
        assert qc["video_stream"] is True
        assert qc["audio_stream"] is True
        assert qc["timing_segments_checked"] == 2
        assert abs(qc["duration_drift_ms"]) <= 80.0

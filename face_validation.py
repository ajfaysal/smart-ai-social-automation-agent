"""Provider-neutral face validation contract for lip-sync.

No face detector is silently substituted here. An actual detector can emit the
same JSON contract later; the router can then reject unsuitable shots safely.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import shutil
import subprocess


@dataclass(frozen=True)
class FaceValidation:
    status: str
    detector: str
    face_count: int
    suitable: bool
    confidence: float
    reason: str


def validate_shot(video: Path, start: float, end: float) -> FaceValidation:
    detector = os.getenv("FACE_DETECTOR", "disabled").strip().lower()
    if detector != "ffmpeg":
        return FaceValidation("not_configured", detector or "disabled", 0, False, 0.0,
                              "No real face detector is configured; lip-sync must not animate this shot.")
    # FFmpeg itself does not provide reliable facial landmarks. Treating this as
    # a detector would be unsafe, so the explicit ffmpeg mode remains rejected.
    return FaceValidation("unsupported", detector, 0, False, 0.0,
                          "FFmpeg scene analysis cannot validate faces or mouth visibility.")


def validate_shots(video: Path, shots: list[dict], output: Path) -> Path:
    records = []
    for shot in shots:
        records.append({
            "shot": shot.get("index"),
            "start": shot.get("start"),
            "end": shot.get("end"),
            **asdict(validate_shot(video, float(shot.get("start", 0)), float(shot.get("end", 0))))
        })
    payload = {
        "version": "1.0",
        "video": str(video.name),
        "detector": os.getenv("FACE_DETECTOR", "disabled"),
        "eligible_shots": sum(1 for x in records if x["suitable"]),
        "total_shots": len(records),
        "records": records,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output

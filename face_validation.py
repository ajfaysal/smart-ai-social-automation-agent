"""Face validation contract with optional local OpenCV detector."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os

from face_detector import detect_frame


@dataclass(frozen=True)
class FaceValidation:
    status: str
    detector: str
    face_count: int
    suitable: bool
    confidence: float
    reason: str
    primary_box: tuple[int, int, int, int] | None = None


def validate_shot(video: Path, start: float, end: float) -> FaceValidation:
    detector = os.getenv("FACE_DETECTOR", "disabled").strip().lower()
    if detector not in {"opencv", "opencv-haar"}:
        return FaceValidation("not_configured", detector or "disabled", 0, False, 0.0,
                              "No real face detector is configured; lip-sync must not animate this shot.")
    try:
        import cv2
    except ImportError:
        return FaceValidation("unavailable", detector, 0, False, 0.0,
                              "OpenCV is not installed.")

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return FaceValidation("error", detector, 0, False, 0.0, "Could not open video.")
    midpoint = max(start, min(end, (start + end) / 2.0))
    cap.set(cv2.CAP_PROP_POS_MSEC, midpoint * 1000.0)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return FaceValidation("error", detector, 0, False, 0.0, "Could not sample the shot.")
    d = detect_frame(frame)
    return FaceValidation(d.status, detector, d.face_count, d.suitable, d.confidence, d.reason, d.primary_box)


def validate_shots(video: Path, shots: list[dict], output: Path) -> Path:
    records = []
    for shot in shots:
        start = float(shot.get("start", 0))
        end = float(shot.get("end", start))
        records.append({
            "shot": shot.get("index"),
            "start": start,
            "end": end,
            **asdict(validate_shot(video, start, end)),
        })
    payload = {
        "version": "1.1",
        "video": video.name,
        "detector": os.getenv("FACE_DETECTOR", "disabled"),
        "eligible_shots": sum(1 for x in records if x["suitable"]),
        "total_shots": len(records),
        "records": records,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output

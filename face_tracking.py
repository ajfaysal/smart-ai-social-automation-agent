"""Conservative per-shot face tracking and mouth-visibility eligibility.

This layer deliberately does not animate faces. It samples frames inside each
shot, tracks the largest detected face by nearest-center matching, and emits a
manifest that downstream lip-sync providers can consume.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math


@dataclass
class TrackSample:
    time: float
    face_count: int
    suitable: bool
    confidence: float
    box: tuple[int, int, int, int] | None


def _center(box):
    x, y, w, h = box
    return x + w / 2.0, y + h / 2.0


def _distance(a, b):
    ax, ay = _center(a)
    bx, by = _center(b)
    return math.hypot(ax - bx, ay - by)


def track_shot(video: Path, start: float, end: float, samples: int = 5) -> dict:
    try:
        import cv2
        from face_detector import detect_frame
    except ImportError:
        return {"status": "unavailable", "eligible": False, "samples": [],
                "reason": "OpenCV face detector is not installed."}

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"status": "error", "eligible": False, "samples": [], "reason": "Could not open video."}
    count = max(2, samples)
    times = [start + (end - start) * i / (count - 1) for i in range(count)]
    records = []
    previous = None
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
        ok, frame = cap.read()
        if not ok:
            continue
        d = detect_frame(frame)
        box = d.primary_box
        if previous is not None and box is not None and _distance(previous, box) > max(frame.shape[:2]) * 0.35:
            box = None
        records.append(asdict(TrackSample(round(t, 3), d.face_count, d.suitable and box is not None,
                                          d.confidence if box is not None else 0.0, box)))
        if box is not None:
            previous = box
    cap.release()
    eligible = len(records) >= 2 and sum(r["suitable"] for r in records) / len(records) >= 0.6
    return {"status": "eligible" if eligible else "rejected", "eligible": eligible,
            "samples": records,
            "reason": "Stable visible face across the shot." if eligible else "Face visibility/tracking was insufficient."}


def build_face_tracks(video: Path, shots: list[dict], output: Path) -> Path:
    records = []
    for shot in shots:
        start = float(shot.get("start", 0))
        end = float(shot.get("end", start))
        records.append({"shot": shot.get("index"), "start": start, "end": end,
                        **track_shot(video, start, end)})
    payload = {
        "version": "1.0",
        "video": video.name,
        "method": "opencv-haar-sampled-center-track",
        "eligible_shots": sum(1 for r in records if r["eligible"]),
        "total_shots": len(records),
        "records": records,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output

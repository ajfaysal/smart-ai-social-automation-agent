"""Conservative per-shot face and mouth tracking eligibility.

This layer does not animate faces. It samples frames inside each shot and only
marks a shot eligible when the primary face remains stable and the mouth region
is detected on a sufficient fraction of samples.
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
    face_suitable: bool
    mouth_visible: bool
    confidence: float
    box: tuple[int, int, int, int] | None
    mouth_box: tuple[int, int, int, int] | None


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
        from mouth_validation import validate_frame as validate_mouth
    except ImportError:
        return {"status": "unavailable", "eligible": False, "samples": [],
                "reason": "OpenCV face/mouth validation dependencies are not installed."}

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"status": "error", "eligible": False, "samples": [], "reason": "Could not open video."}
    count = max(2, samples)
    times = [start + (end - start) * i / (count - 1) for i in range(count)]
    records = []
    previous = None
    mouth_configured = __import__("os").getenv("MOUTH_LANDMARK_PROVIDER", "disabled").strip().lower() in {"opencv-haar-mouth", "opencv"}
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
        ok, frame = cap.read()
        if not ok:
            continue
        d = detect_frame(frame)
        box = d.primary_box
        if previous is not None and box is not None and _distance(previous, box) > max(frame.shape[:2]) * 0.35:
            box = None
        m = validate_mouth(frame) if box is not None else None
        mouth_visible = bool(m and m.mouth_visible and box is not None)
        records.append(asdict(TrackSample(round(t, 3), d.face_count, d.suitable and box is not None,
                                          mouth_visible, m.confidence if m else 0.0, box,
                                          m.mouth_box if m and mouth_visible else None)))
        if box is not None:
            previous = box
    cap.release()
    face_ratio = sum(r["face_suitable"] for r in records) / len(records) if records else 0.0
    mouth_ratio = sum(r["mouth_visible"] for r in records) / len(records) if records else 0.0
    eligible = mouth_configured and len(records) >= 2 and face_ratio >= 0.6 and mouth_ratio >= 0.6
    if not mouth_configured:
        reason = "Mouth landmark provider is not configured; shot remains fallback-only."
        status = "mouth_validation_not_configured"
    elif eligible:
        reason = "Stable face and visible mouth across the shot."
        status = "eligible"
    else:
        reason = "Face tracking or mouth visibility was insufficient."
        status = "rejected"
    return {"status": status, "eligible": eligible, "samples": records,
            "face_ratio": round(face_ratio, 3), "mouth_ratio": round(mouth_ratio, 3),
            "reason": reason}


def build_face_tracks(video: Path, shots: list[dict], output: Path) -> Path:
    records = []
    for shot in shots:
        start = float(shot.get("start", 0)); end = float(shot.get("end", start))
        records.append({"shot": shot.get("index"), "start": start, "end": end,
                        **track_shot(video, start, end)})
    payload = {"version": "1.1", "video": video.name,
               "method": "opencv-haar-face-plus-mouth-sampled-track",
               "eligible_shots": sum(1 for r in records if r["eligible"]),
               "total_shots": len(records), "records": records}
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output

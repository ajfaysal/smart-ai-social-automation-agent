"""Optional local face validation using OpenCV Haar cascades.

The dependency is optional. Without OpenCV, the detector reports unavailable
rather than pretending that faces were detected.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json


@dataclass(frozen=True)
class Detection:
    face_count: int
    suitable: bool
    confidence: float
    status: str
    reason: str
    primary_box: tuple[int, int, int, int] | None = None


def detect_frame(frame) -> Detection:
    try:
        import cv2
    except ImportError:
        return Detection(0, False, 0.0, "unavailable", "OpenCV is not installed.")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
    boxes = list(faces)
    if not boxes:
        return Detection(0, False, 0.0, "no_face", "No frontal face detected.")
    box = max(boxes, key=lambda b: int(b[2]) * int(b[3]))
    area = int(box[2]) * int(box[3])
    frame_area = max(1, frame.shape[0] * frame.shape[1])
    confidence = min(1.0, max(0.0, area / (frame_area * 0.08)))
    suitable = confidence >= 0.5
    return Detection(len(boxes), suitable, round(confidence, 3), "ok" if suitable else "small_face",
                     "Frontal face candidate detected." if suitable else "Face is too small for safe animation.",
                     tuple(int(v) for v in box))


def validate_video_sample(video: Path, sample_seconds: float = 1.0) -> dict:
    try:
        import cv2
    except ImportError:
        return {"status": "unavailable", "detector": "opencv-haar", "reason": "OpenCV is not installed.", "samples": []}
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"status": "error", "detector": "opencv-haar", "reason": "Could not open video.", "samples": []}
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total / fps if total else 0.0
    times = [0.0, max(0.0, duration / 2), max(0.0, duration - 0.05)] if duration else [0.0]
    samples = []
    for t in sorted(set(round(x, 3) for x in times)):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if ok:
            d = detect_frame(frame)
            samples.append({"time": t, **asdict(d)})
    cap.release()
    eligible = sum(1 for x in samples if x["suitable"])
    return {"status": "ok", "detector": "opencv-haar", "duration": round(duration, 3), "eligible_samples": eligible, "samples": samples}

"""Optional mouth/landmark validation for lip-sync eligibility.

This is deliberately provider-neutral. OpenCV Haar remains the lightweight
fallback; a real landmark backend can be enabled through MOUTH_LANDMARK_PROVIDER.
No shot is marked mouth-eligible merely because a face was detected.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class MouthValidation:
    status: str
    provider: str
    face_count: int
    mouth_visible: bool
    confidence: float
    reason: str
    mouth_box: tuple[int, int, int, int] | None = None


def validate_frame(frame) -> MouthValidation:
    provider = os.getenv("MOUTH_LANDMARK_PROVIDER", "disabled").strip().lower()
    if provider not in {"opencv-haar-mouth", "opencv"}:
        return MouthValidation("not_configured", provider, 0, False, 0.0,
                               "A landmark-capable mouth detector is not configured.")
    try:
        import cv2
    except ImportError:
        return MouthValidation("unavailable", provider, 0, False, 0.0,
                               "OpenCV is not installed.")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    mouth_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")
    faces = list(face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48)))
    if not faces:
        return MouthValidation("no_face", provider, 0, False, 0.0, "No frontal face detected.")

    face = max(faces, key=lambda b: int(b[2]) * int(b[3]))
    x, y, w, h = [int(v) for v in face]
    lower = gray[y + int(h * 0.45): y + h, x: x + w]
    mouths = [] if lower.size == 0 else list(mouth_cascade.detectMultiScale(
        lower, scaleFactor=1.1, minNeighbors=8, minSize=(max(16, int(w * 0.16)), max(8, int(h * 0.08)))
    ))
    if not mouths:
        return MouthValidation("no_mouth", provider, len(faces), False, 0.0,
                               "Face detected but mouth region was not confidently detected.", None)

    mx, my, mw, mh = max(mouths, key=lambda b: int(b[2]) * int(b[3]))
    mouth_box = (x + int(mx), y + int(h * 0.45) + int(my), int(mw), int(mh))
    ratio = (int(mw) * int(mh)) / max(1, w * h)
    confidence = min(1.0, max(0.0, ratio / 0.035))
    suitable = confidence >= 0.45
    return MouthValidation("ok" if suitable else "small_mouth", provider, len(faces), suitable,
                           round(confidence, 3),
                           "Mouth candidate detected in the primary face." if suitable else "Mouth candidate is too small for safe animation.",
                           mouth_box)


def validate_video_sample(video: Path, sample_times: list[float]) -> dict:
    try:
        import cv2
    except ImportError:
        return {"status": "unavailable", "provider": os.getenv("MOUTH_LANDMARK_PROVIDER", "disabled"), "samples": []}
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"status": "error", "provider": os.getenv("MOUTH_LANDMARK_PROVIDER", "disabled"), "samples": []}
    samples = []
    for t in sample_times:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, float(t)) * 1000)
        ok, frame = cap.read()
        if ok:
            samples.append({"time": round(float(t), 3), **asdict(validate_frame(frame))})
    cap.release()
    eligible = sum(1 for x in samples if x["mouth_visible"])
    return {"status": "ok", "provider": os.getenv("MOUTH_LANDMARK_PROVIDER", "disabled"),
            "eligible_samples": eligible, "samples": samples}

"""Temporal face/mouth tracking for conservative shot-level lip-sync routing."""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrackSample:
    time: float
    face_count: int
    face_suitable: bool
    mouth_visible: bool
    confidence: float
    box: tuple[int, int, int, int] | None
    mouth_box: tuple[int, int, int, int] | None
    mouth_provider: str


def _center(box):
    if not box:
        return None
    x, y, w, h = box
    return (x + w / 2.0, y + h / 2.0)


def _distance(a, b):
    if a is None or b is None:
        return 1.0
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return (dx * dx + dy * dy) ** 0.5


def track_shot(video: Path, start: float, end: float, samples: int = 7) -> dict:
    """Sample a shot and require temporal face + mouth consistency.

    Eligibility requires configured mouth landmarks, at least 70% valid samples,
    at least 4 valid samples, and stable primary-face motion. This is a routing
    gate only; it does not animate lips itself.
    """
    try:
        import cv2
        from face_detector import detect_frame
        from mouth_validation import validate_frame
    except ImportError as exc:
        return {"status": "unavailable", "eligible": False, "reason": str(exc), "samples": []}

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"status": "error", "eligible": False, "reason": "Could not open video.", "samples": []}
    count = max(4, int(samples))
    times = [start + (end - start) * i / max(1, count - 1) for i in range(count)]
    records: list[TrackSample] = []
    centers = []
    try:
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000)
            ok, frame = cap.read()
            if not ok:
                continue
            face = detect_frame(frame)
            mouth = validate_frame(frame)
            rec = TrackSample(
                time=round(t, 3),
                face_count=face.face_count,
                face_suitable=bool(face.suitable),
                mouth_visible=bool(mouth.mouth_visible),
                confidence=round(min(face.confidence, mouth.confidence) if mouth.mouth_visible else 0.0, 3),
                box=face.primary_box,
                mouth_box=mouth.mouth_box,
                mouth_provider=mouth.provider,
            )
            records.append(rec)
            if rec.face_suitable and rec.mouth_visible and rec.box:
                centers.append(_center(rec.box))
    finally:
        cap.release()

    configured_provider = os.getenv("MOUTH_LANDMARK_PROVIDER", os.getenv("LANDMARK_PROVIDER", "disabled")).strip().lower()
    valid = [r for r in records if r.face_suitable and r.mouth_visible]
    ratio = len(valid) / max(1, len(records))
    stable = True
    if len(centers) >= 2:
        # Normalized face-center motion threshold. Large jumps indicate tracking
        # a different face or a shot with unreliable framing.
        frame_w = frame.shape[1] if 'frame' in locals() and frame is not None else 1920
        frame_h = frame.shape[0] if 'frame' in locals() and frame is not None else 1080
        diagonal = max(1.0, (frame_w * frame_w + frame_h * frame_h) ** 0.5)
        stable = max(_distance(a, b) for a, b in zip(centers, centers[1:])) / diagonal <= 0.22

    eligible = configured_provider in {"mediapipe"} and len(valid) >= 4 and ratio >= 0.70 and stable
    if eligible:
        status, reason = "eligible", "Temporal face and mouth validation passed."
    elif configured_provider not in {"mediapipe"}:
        status, reason = "mouth_validation_not_configured", "A landmark-capable mouth provider is required."
    elif len(valid) < 4 or ratio < 0.70:
        status, reason = "rejected", f"Insufficient temporal mouth visibility: {len(valid)}/{len(records)} samples."
    else:
        status, reason = "rejected", "Primary face track is not temporally stable."
    return {
        "status": status,
        "eligible": eligible,
        "reason": reason,
        "mouth_provider": configured_provider,
        "valid_samples": len(valid),
        "total_samples": len(records),
        "visibility_ratio": round(ratio, 3),
        "track_stable": stable,
        "samples": [asdict(r) for r in records],
    }


def build_face_tracks(video: Path, shots: list[dict]) -> dict:
    records = []
    for shot in shots:
        records.append({"shot": int(shot.get("index", len(records))), **track_shot(video, float(shot.get("start", 0)), float(shot.get("end", 0)))})
    return {
        "version": "1.3",
        "mode": "temporal-face-track-plus-landmark-mouth-gate",
        "eligible_shots": sum(bool(r.get("eligible")) for r in records),
        "total_shots": len(records),
        "records": records,
    }

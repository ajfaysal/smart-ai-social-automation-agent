"""Temporal face/mouth tracking for conservative shot-level lip-sync routing."""
from __future__ import annotations

import json
import math
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
    return x + w / 2.0, y + h / 2.0


def _distance(a, b):
    ca, cb = _center(a), _center(b)
    if ca is None or cb is None:
        return float("inf")
    return math.hypot(ca[0] - cb[0], ca[1] - cb[1])


def tracking_eligibility(records: list[dict], provider: str) -> tuple[bool, str]:
    """Pure decision helper so routing rules can be unit-tested without video."""
    valid = [r for r in records if r.get("face_suitable") and r.get("mouth_visible")]
    total = len(records)
    face_ratio = sum(bool(r.get("face_suitable")) for r in records) / total if total else 0.0
    mouth_ratio = sum(bool(r.get("mouth_visible")) for r in records) / total if total else 0.0
    stable = all(bool(r.get("track_stable", True)) for r in records)
    configured = provider in {"mediapipe"}
    eligible = configured and total >= 4 and len(valid) >= 4 and face_ratio >= 0.70 and mouth_ratio >= 0.70 and stable
    if not configured:
        return False, "A landmark-capable mouth provider is required."
    if total < 4 or len(valid) < 4 or face_ratio < 0.70 or mouth_ratio < 0.70:
        return False, f"Insufficient temporal mouth visibility: {len(valid)}/{total} valid samples."
    if not stable:
        return False, "Primary face track is not temporally stable."
    return eligible, "Temporal face and mouth validation passed."


def track_shot(video: Path, start: float, end: float, samples: int = 7) -> dict:
    """Sample a shot and require temporal face + landmark-mouth consistency."""
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
    previous_box = None
    frame_size = None
    try:
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
            ok, frame = cap.read()
            if not ok:
                continue
            frame_size = frame.shape[:2]
            detection = detect_frame(frame)
            box = detection.primary_box
            if previous_box is not None and box is not None:
                diagonal = max(1.0, math.hypot(frame.shape[1], frame.shape[0]))
                if _distance(previous_box, box) / diagonal > 0.22:
                    box = None
            mouth = validate_frame(frame) if box is not None else None
            visible = bool(mouth and mouth.mouth_visible and box is not None)
            records.append(asdict(TrackSample(
                time=round(t, 3),
                face_count=detection.face_count,
                face_suitable=bool(detection.suitable and box is not None),
                mouth_visible=visible,
                confidence=round(float(mouth.confidence) if mouth and visible else 0.0, 3),
                box=box,
                mouth_box=mouth.mouth_box if mouth and visible else None,
                mouth_provider=mouth.provider if mouth else os.getenv("MOUTH_LANDMARK_PROVIDER", "disabled"),
            )))
            if box is not None:
                previous_box = box
    finally:
        cap.release()

    provider = os.getenv("MOUTH_LANDMARK_PROVIDER", os.getenv("LANDMARK_PROVIDER", "disabled")).strip().lower()
    stable = True
    valid_boxes = [r["box"] for r in records if r.get("face_suitable") and r.get("box")]
    if len(valid_boxes) >= 2 and frame_size:
        diagonal = max(1.0, math.hypot(frame_size[1], frame_size[0]))
        stable = max(_distance(a, b) for a, b in zip(valid_boxes, valid_boxes[1:])) / diagonal <= 0.22
    for record in records:
        record["track_stable"] = stable

    eligible, reason = tracking_eligibility(records, provider)
    status = "eligible" if eligible else ("mouth_validation_not_configured" if provider != "mediapipe" else "rejected")
    return {
        "status": status,
        "eligible": eligible,
        "reason": reason,
        "mouth_provider": provider,
        "valid_samples": sum(1 for r in records if r["face_suitable"] and r["mouth_visible"]),
        "total_samples": len(records),
        "face_ratio": round(sum(bool(r["face_suitable"]) for r in records) / max(1, len(records)), 3),
        "mouth_ratio": round(sum(bool(r["mouth_visible"]) for r in records) / max(1, len(records)), 3),
        "track_stable": stable,
        "samples": records,
    }


def build_face_tracks(video: Path, shots: list[dict], output: Path) -> Path:
    records = []
    for shot in shots:
        start = float(shot.get("start", 0))
        end = float(shot.get("end", start))
        records.append({"shot": shot.get("index"), "start": start, "end": end, **track_shot(video, start, end)})
    payload = {
        "version": "1.3",
        "video": video.name,
        "method": "temporal-face-track-plus-landmark-mouth-gate",
        "eligible_shots": sum(1 for r in records if r["eligible"]),
        "total_shots": len(records),
        "records": records,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output

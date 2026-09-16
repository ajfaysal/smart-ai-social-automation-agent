"""Optional OCR-guided removal of burned-in drama text.

This module intentionally does not touch audio. It detects visible text boxes and
reconstructs the covered pixels with OpenCV inpainting. For long dramas, OCR is
sampled rather than run on every frame. The latest validated mask is carried
until the next sample, with scene cuts resetting the mask. Fixed watermark or
sticker regions can be supplied as normalized coordinates.

This is a best-effort pixel restoration stage, not a guarantee that every
persistent watermark can be perfectly reconstructed. The caller should keep the
returned report and run final visual QC.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np


class TextCleanerUnavailable(RuntimeError):
    pass


def _load_reader(languages: list[str]):
    try:
        import easyocr  # type: ignore
    except Exception as exc:
        raise TextCleanerUnavailable("EasyOCR is not installed; text cleanup is unavailable.") from exc
    return easyocr.Reader(languages, gpu=os.getenv("TEXT_CLEANER_GPU", "1") != "0", verbose=False)


def _boxes(reader, frame: np.ndarray, min_confidence: float) -> list[tuple[int, int, int, int, float, str]]:
    detections = reader.readtext(frame, detail=1, paragraph=False)
    result: list[tuple[int, int, int, int, float, str]] = []
    for item in detections:
        if len(item) < 3:
            continue
        polygon, text, confidence = item
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            continue
        if confidence < min_confidence or not str(text).strip():
            continue
        pts = np.asarray(polygon, dtype=np.int32).reshape(-1, 2)
        x, y, w, h = cv2.boundingRect(pts)
        if w >= 3 and h >= 3:
            result.append((x, y, x + w, y + h, confidence, str(text)))
    return result


def _region_mask(shape: tuple[int, int], regions: list[dict[str, float]], dilation: int) -> np.ndarray:
    height, width = shape
    mask = np.zeros((height, width), dtype=np.uint8)
    for region in regions:
        x = int(float(region.get("x", 0)) * width)
        y = int(float(region.get("y", 0)) * height)
        w = int(float(region.get("w", 0)) * width)
        h = int(float(region.get("h", 0)) * height)
        if w <= 0 or h <= 0:
            continue
        cv2.rectangle(mask, (max(0, x), max(0, y)), (min(width - 1, x + w), min(height - 1, y + h)), 255, -1)
    if dilation > 0:
        kernel = np.ones((dilation, dilation), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
    return mask


def clean_video(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    languages: list[str] | None = None,
    sample_every_frames: int = 15,
    min_confidence: float = 0.45,
    dilation: int = 5,
    fixed_regions: list[dict[str, float]] | None = None,
    scene_cuts: list[float] | None = None,
) -> dict[str, Any]:
    """Remove OCR-detected visible text and fixed configured regions.

    The input may contain any audio; this function produces a video-only file.
    The dubbing pipeline should attach the final mastered audio afterwards.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    report_path = Path(report_path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if sample_every_frames < 1:
        raise ValueError("sample_every_frames must be >= 1")

    reader = _load_reader(languages or ["ch_sim", "en"])
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError("Could not open input video.")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if width <= 0 or height <= 0:
        cap.release()
        raise RuntimeError("Invalid input video dimensions.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError("Could not create cleanup video.")

    cuts = sorted(float(x) for x in (scene_cuts or []) if float(x) > 0)
    cut_frames = {int(round(x * fps)) for x in cuts}
    active: list[tuple[int, int, int, int, float, str]] = []
    sampled = 0
    removed_boxes = 0
    frame_index = 0
    confidence_sum = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index in cut_frames:
                active = []
            if frame_index % sample_every_frames == 0:
                active = _boxes(reader, frame, min_confidence)
                sampled += 1
                removed_boxes += len(active)
                confidence_sum += sum(x[4] for x in active)

            mask = np.zeros((height, width), dtype=np.uint8)
            for x1, y1, x2, y2, _, _ in active:
                cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
            if fixed_regions:
                mask = cv2.bitwise_or(mask, _region_mask((height, width), fixed_regions, dilation))
            elif np.any(mask):
                kernel = np.ones((dilation, dilation), np.uint8)
                mask = cv2.dilate(mask, kernel, iterations=1)

            if np.any(mask):
                # Telea is fast enough for long-drama CPU fallback. A future
                # temporal/LaMa provider can replace this implementation without
                # changing the pipeline contract.
                cleaned = cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)
                writer.write(cleaned)
            else:
                writer.write(frame)
            frame_index += 1
    finally:
        cap.release()
        writer.release()

    if frame_index == 0:
        raise RuntimeError("No video frames were processed.")
    report = {
        "version": "1.0",
        "provider": "easyocr-opencv-inpaint",
        "input": str(input_path),
        "output": str(output_path),
        "fps": fps,
        "frames": frame_index,
        "sample_every_frames": sample_every_frames,
        "ocr_samples": sampled,
        "detected_text_boxes": removed_boxes,
        "mean_detection_confidence": round(confidence_sum / removed_boxes, 4) if removed_boxes else 0.0,
        "fixed_regions": fixed_regions or [],
        "scene_cut_resets": len(cut_frames),
        "audio": "not_modified; final mastered audio must be attached after cleanup",
        "quality_note": "Best-effort spatial inpainting; persistent text over complex/moving content may require temporal or neural restoration.",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

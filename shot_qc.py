"""Deterministic QC for shot-aware lip-sync reassembly."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess


def _duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def validate_shot_plan(shots: list[dict], expected_duration: float, tolerance: float = 0.08) -> dict:
    ordered = sorted(shots, key=lambda x: float(x.get("start", 0)))
    gaps, overlaps = [], []
    cursor = 0.0
    for shot in ordered:
        start, end = float(shot.get("start", 0)), float(shot.get("end", 0))
        if end <= start:
            raise RuntimeError(f"QC failed: invalid shot {shot.get('index')}: end <= start")
        if start - cursor > tolerance:
            gaps.append({"from": round(cursor, 3), "to": round(start, 3)})
        if cursor - start > tolerance:
            overlaps.append({"from": round(start, 3), "to": round(cursor, 3)})
        cursor = max(cursor, end)
    tail_gap = expected_duration - cursor
    if tail_gap > tolerance:
        gaps.append({"from": round(cursor, 3), "to": round(expected_duration, 3)})
    if -tail_gap > tolerance:
        overlaps.append({"from": round(expected_duration, 3), "to": round(cursor, 3)})
    if gaps or overlaps:
        raise RuntimeError(f"QC failed: shot coverage has {len(gaps)} gaps and {len(overlaps)} overlaps.")
    return {"status":"pass","shots_checked":len(ordered),"coverage_start":round(float(ordered[0].get("start",0)) if ordered else 0,3),"coverage_end":round(cursor,3),"gaps":0,"overlaps":0}


def validate_reassembled(path: Path, expected_duration: float, shots: list[dict], tolerance: float = 0.08) -> dict:
    plan = validate_shot_plan(shots, expected_duration, tolerance)
    actual = _duration(path)
    drift_ms = (actual - expected_duration) * 1000
    if abs(drift_ms) > tolerance * 1000:
        raise RuntimeError(f"QC failed: reassembled duration drift is {drift_ms:+.1f}ms.")
    return {**plan,"output_duration_seconds":round(actual,3),"duration_drift_ms":round(drift_ms,1)}

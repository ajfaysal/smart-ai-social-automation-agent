"""Timing-lock quality control for dubbing TTS clips."""
from __future__ import annotations

import subprocess
from pathlib import Path

def _duration(path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Cannot read audio duration: {path}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Invalid audio duration: {path}") from exc

def validate_timing_lock(fitted_path: Path, target_seconds: float, *, raw_path: Path | None = None, tolerance_seconds: float = 0.035, max_speed_ratio: float = 2.0) -> dict:
    """Fail closed when a fitted TTS clip drifts or requires extreme acceleration."""
    if target_seconds <= 0:
        raise RuntimeError("Timing target must be positive.")
    fitted_duration = _duration(fitted_path)
    drift = fitted_duration - target_seconds
    raw_duration = None
    speed_ratio = None
    if raw_path is not None:
        raw_duration = _duration(raw_path)
        if raw_duration <= 0:
            raise RuntimeError(f"Raw TTS duration is invalid: {raw_path}")
        speed_ratio = raw_duration / target_seconds
        if speed_ratio > max_speed_ratio:
            raise RuntimeError(f"TTS timing requires excessive acceleration: {speed_ratio:.3f}x > {max_speed_ratio:.3f}x")
    if abs(drift) > tolerance_seconds:
        raise RuntimeError(f"TTS timing lock drift is {drift * 1000:.1f}ms, outside ±{tolerance_seconds * 1000:.1f}ms.")
    return {"fitted_path": str(fitted_path), "target_seconds": round(target_seconds, 6), "fitted_duration_seconds": round(fitted_duration, 6), "drift_seconds": round(drift, 6), "drift_ms": round(drift * 1000, 3), "raw_duration_seconds": round(raw_duration, 6) if raw_duration is not None else None, "speed_ratio": round(speed_ratio, 6) if speed_ratio is not None else None, "tolerance_ms": round(tolerance_seconds * 1000, 3), "max_speed_ratio": max_speed_ratio, "timing_lock": True}

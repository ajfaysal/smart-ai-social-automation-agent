"""Production preflight for scene-aware lip-sync.

This module deliberately separates analysis from animation. It can be used by
an installed lip-sync engine to decide whether a shot is safe to process.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import subprocess


@dataclass(frozen=True)
class Shot:
    start: float
    end: float
    index: int


@dataclass(frozen=True)
class LipSyncPreflight:
    provider: str
    available: bool
    shot_count: int
    status: str
    reason: str


def _scene_times(video: Path, threshold: float = 0.38) -> list[float]:
    command = [
        "ffmpeg", "-hide_banner", "-i", str(video),
        "-filter_complex", f"select='gt(scene,{threshold})',showinfo",
        "-an", "-f", "null", "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:] or "FFmpeg scene analysis failed")
    times = [0.0]
    for line in result.stderr.splitlines():
        marker = "pts_time:"
        if marker in line:
            try:
                times.append(float(line.split(marker, 1)[1].split()[0]))
            except (IndexError, ValueError):
                continue
    return sorted(set(round(t, 3) for t in times))


def analyze_shots(video: Path, threshold: float = 0.38) -> list[Shot]:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())
    cuts = [t for t in _scene_times(video, threshold) if 0 < t < duration]
    boundaries = [0.0, *cuts, duration]
    return [Shot(boundaries[i], boundaries[i + 1], i + 1)
            for i in range(len(boundaries) - 1) if boundaries[i + 1] > boundaries[i]]


def preflight(video: Path, provider) -> LipSyncPreflight:
    shots = analyze_shots(video)
    if not provider.available():
        return LipSyncPreflight(
            provider=provider.name,
            available=False,
            shot_count=len(shots),
            status="fallback",
            reason="No configured real lip-sync runtime/model; preserve original video frames.",
        )
    return LipSyncPreflight(
        provider=provider.name,
        available=True,
        shot_count=len(shots),
        status="ready",
        reason="Provider is configured; shot-aware processing can proceed after face validation.",
    )


def write_preflight(video: Path, provider, output: Path) -> Path:
    result = preflight(video, provider)
    payload = asdict(result)
    payload["face_validation"] = "provider_required"
    payload["shots"] = [asdict(x) for x in analyze_shots(video)]
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output

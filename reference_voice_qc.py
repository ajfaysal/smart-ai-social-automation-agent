"""Quality control for runtime speaker-reference audio clips.

Reference clips are runtime artifacts and must be clean enough for voice cloning.
This module intentionally validates the normalized WAV produced by the extraction
pipeline without storing audio or model weights in git.
"""
from __future__ import annotations

import math
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReferenceVoiceQC:
    path: str
    duration_seconds: float
    sample_rate: int
    channels: int
    sample_width: int
    silence_ratio: float
    status: str
    reason: str | None = None
    selection_score: float | None = None


def _silence_ratio(path: Path, threshold: float = 0.008, chunk_frames: int = 1600) -> float:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        width = wav.getsampwidth()
        channels = wav.getnchannels()
        raw = wav.readframes(frames)
    if width != 2:
        raise ValueError("reference audio must be 16-bit PCM")
    frame_bytes = width * channels
    silent = 0
    total = 0
    for offset in range(0, frames, chunk_frames):
        count = min(chunk_frames, frames - offset)
        chunk = raw[offset * frame_bytes:(offset + count) * frame_bytes]
        samples = []
        for i in range(0, len(chunk), 2):
            value = int.from_bytes(chunk[i:i + 2], "little", signed=True) / 32768.0
            samples.append(value)
        if not samples:
            continue
        rms = math.sqrt(sum(v * v for v in samples) / len(samples))
        total += count
        if rms < threshold:
            silent += count
    return silent / total if total else 1.0


def validate_reference_voice(
    path: Path,
    *,
    min_seconds: float = 1.5,
    max_seconds: float = 8.0,
    max_silence_ratio: float = 0.65,
) -> ReferenceVoiceQC:
    """Fail closed on missing, malformed, too-short, too-long, or mostly-silent references."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"reference voice is missing or empty: {path}")
    try:
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            width = wav.getsampwidth()
            frames = wav.getnframes()
            duration = frames / sample_rate if sample_rate else 0.0
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"reference voice is not a decodable WAV: {path}") from exc

    if channels != 1 or sample_rate != 16000 or width != 2:
        raise ValueError(
            f"reference voice must be mono 16 kHz PCM16: channels={channels}, "
            f"sample_rate={sample_rate}, sample_width={width}"
        )
    if duration < min_seconds:
        raise ValueError(f"reference voice is too short: {duration:.3f}s")
    if duration > max_seconds + 0.05:
        raise ValueError(f"reference voice exceeds maximum duration: {duration:.3f}s")

    silence = _silence_ratio(path)
    if silence > max_silence_ratio:
        raise ValueError(f"reference voice is mostly silent: {silence:.3f}")

    return ReferenceVoiceQC(
        path=str(path),
        duration_seconds=round(duration, 4),
        sample_rate=sample_rate,
        channels=channels,
        sample_width=width,
        silence_ratio=round(silence, 4),
        status="SUCCEEDED",
    )


def qc_dict(path: Path, **kwargs) -> dict:
    return asdict(validate_reference_voice(path, **kwargs))

"""Speaker identity and reference-voice metadata for high-character-count dubbing.

This module deliberately separates *who is speaking* from *which TTS engine speaks*.
The diarization backend is pluggable; CI can use deterministic fixture segments while
GPU runners can connect pyannote or 3D-Speaker through runtime adapters.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SpeakerTurn:
    speaker_id: str
    start: float
    end: float
    confidence: float = 1.0


@dataclass(frozen=True)
class CharacterIdentity:
    character_id: str
    speaker_id: str
    confidence: float
    reference_audio: str | None
    gender_hint: str = "unknown"


@dataclass(frozen=True)
class DiarizationResult:
    backend: str
    status: str
    turns: tuple[SpeakerTurn, ...]
    speaker_count: int
    error: str | None = None


def normalize_speaker_id(value: str) -> str:
    """Normalize backend-specific speaker labels to stable SNN identifiers."""
    raw = str(value).strip()
    if raw.upper().startswith("SPEAKER_"):
        suffix = raw.split("_", 1)[1]
        if suffix.isdigit():
            return f"S{int(suffix) + 1:02d}"
    if raw.startswith("S") and raw[1:].isdigit():
        return f"S{int(raw[1:]):02d}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return f"SX{digest}"


def character_map(turns: Iterable[SpeakerTurn], minimum_confidence: float = 0.70) -> dict[str, CharacterIdentity]:
    """Create a deterministic character identity for each sufficiently confident speaker."""
    speakers: dict[str, list[float]] = {}
    for turn in turns:
        sid = normalize_speaker_id(turn.speaker_id)
        speakers.setdefault(sid, []).append(float(turn.confidence))

    result: dict[str, CharacterIdentity] = {}
    for index, sid in enumerate(sorted(speakers)):
        confidence = sum(speakers[sid]) / len(speakers[sid])
        if confidence < minimum_confidence:
            continue
        result[sid] = CharacterIdentity(
            character_id=f"C{index + 1:02d}",
            speaker_id=sid,
            confidence=round(confidence, 4),
            reference_audio=None,
        )
    return result


def write_identity_manifest(
    path: Path,
    diarization: DiarizationResult,
    identities: dict[str, CharacterIdentity],
) -> None:
    """Persist only metadata; never copy voice samples into the repository."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "backend": diarization.backend,
        "status": diarization.status,
        "speaker_count": diarization.speaker_count,
        "error": diarization.error,
        "turns": [asdict(t) for t in diarization.turns],
        "characters": [asdict(v) for v in identities.values()],
        "media_policy": "metadata-only-no-reference-audio-committed",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_reference_clip(audio: Path, speaker_id: str, start: float, end: float, output_dir: Path) -> Path:
    """Extract a clean reference clip to runtime storage using ffmpeg."""
    if end <= start:
        raise ValueError("Reference clip end must be greater than start")
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = normalize_speaker_id(speaker_id)
    output = output_dir / f"{safe}.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
            "-i", str(audio), "-vn", "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(f"Reference extraction failed: {output}")
    return output


def run_diarization_command(audio: Path, backend: str, output_json: Path) -> DiarizationResult:
    """Run a configured diarization backend without embedding model weights in git."""
    env_name = {
        "pyannote": "PYANNOTE_DIARIZATION_COMMAND",
        "3d-speaker": "THREE_D_SPEAKER_DIARIZATION_COMMAND",
    }.get(backend)
    if not env_name:
        return DiarizationResult(backend, "SKIPPED", tuple(), 0, f"Unsupported backend: {backend}")
    command = os.getenv(env_name, "")
    if not command:
        return DiarizationResult(backend, "UNAVAILABLE", tuple(), 0, f"Missing {env_name}")

    rendered = command.format(audio=str(audio), output=str(output_json))
    try:
        subprocess.run(shlex.split(rendered), check=True, capture_output=True, text=True)
        data = json.loads(output_json.read_text(encoding="utf-8"))
        turns = tuple(
            SpeakerTurn(str(item["speaker"]), float(item["start"]), float(item["end"]), float(item.get("confidence", 1.0)))
            for item in data.get("turns", [])
        )
        speakers = {normalize_speaker_id(t.speaker_id) for t in turns}
        return DiarizationResult(backend, "SUCCEEDED", turns, len(speakers))
    except Exception as exc:
        return DiarizationResult(backend, "FAILED", tuple(), 0, str(exc))

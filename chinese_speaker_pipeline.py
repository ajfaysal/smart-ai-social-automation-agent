"""Runtime orchestration for Chinese speaker diarization and voice-bank extraction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from speaker_identity import (
    character_map,
    extract_best_reference_clips,
    normalize_speaker_id,
    run_diarization_command,
    write_identity_manifest,
)


def build_voice_bank(audio: Path, backend: str, manifest: Path, reference_dir: Path | None = None) -> dict:
    raw = manifest.with_suffix(".diarization.json")
    result = run_diarization_command(audio, backend, raw)
    identities = character_map(result.turns)

    if result.status == "SUCCEEDED" and reference_dir:
        references = extract_best_reference_clips(audio, result.turns, reference_dir)
        for sid, ref in references.items():
            if sid in identities:
                identity = identities[sid]
                identities[sid] = type(identity)(
                    identity.character_id,
                    identity.speaker_id,
                    identity.confidence,
                    str(ref),
                    identity.gender_hint,
                )

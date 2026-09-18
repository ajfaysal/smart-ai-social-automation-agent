"""Runtime orchestration for Chinese speaker diarization and voice-bank extraction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from speaker_identity import (
    character_map,
    extract_best_reference_clips_with_qc,
    run_diarization_command,
    write_identity_manifest,
)


def build_voice_bank(audio: Path, backend: str, manifest: Path, reference_dir: Path | None = None) -> dict:
    """Build speaker identities and attach auditable reference-voice evidence."""
    raw = manifest.with_suffix(".diarization.json")
    result = run_diarization_command(audio, backend, raw)
    identities = character_map(result.turns)

    if result.status == "SUCCEEDED" and reference_dir:
        selected = extract_best_reference_clips_with_qc(audio, result.turns, reference_dir)
        for sid, (ref, qc, selection_score) in selected.items():
            if sid in identities:
                identity = identities[sid]
                identities[sid] = type(identity)(
                    identity.character_id,
                    identity.speaker_id,
                    identity.confidence,
                    str(ref),
                    identity.gender_hint,
                    qc,
                    selection_score,
                )

    write_identity_manifest(manifest, result, identities)
    return json.loads(manifest.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path)
    args = parser.parse_args()
    build_voice_bank(args.audio, args.backend, args.manifest, args.reference_dir)


if __name__ == "__main__":
    main()

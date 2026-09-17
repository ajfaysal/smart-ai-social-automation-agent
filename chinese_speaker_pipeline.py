"""Runtime orchestration for Chinese speaker diarization and voice-bank extraction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from speaker_identity import character_map, extract_reference_clip, run_diarization_command, write_identity_manifest


def build_voice_bank(audio: Path, backend: str, manifest: Path, reference_dir: Path | None = None) -> dict:
    raw = manifest.with_suffix(".diarization.json")
    result = run_diarization_command(audio, backend, raw)
    identities = character_map(result.turns)

    if result.status == "SUCCEEDED" and reference_dir:
        for sid, identity in list(identities.items()):
            turns = [t for t in result.turns if t.speaker_id == sid or t.speaker_id == sid.replace("S", "SPEAKER_")]
            if not turns:
                continue
            turn = max(turns, key=lambda item: (item.end - item.start) * item.confidence)
            duration = min(30.0, max(1.0, turn.end - turn.start))
            try:
                ref = extract_reference_clip(audio, sid, turn.start, turn.start + duration, reference_dir)
                identities[sid] = type(identity)(identity.character_id, identity.speaker_id, identity.confidence, str(ref), identity.gender_hint)
            except Exception:
                pass

    write_identity_manifest(manifest, result, identities)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--backend", choices=["pyannote", "3d-speaker"], default="pyannote")
    parser.add_argument("--manifest", type=Path, default=Path("validation-artifacts/speaker-identity.json"))
    parser.add_argument("--reference-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_voice_bank(args.audio, args.backend, args.manifest, args.reference_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

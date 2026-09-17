from pathlib import Path

import chinese_speaker_pipeline as pipeline
from speaker_identity import DiarizationResult, SpeakerTurn, character_map


def test_voice_bank_matches_backend_speaker_labels_after_normalization(tmp_path: Path, monkeypatch):
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"fixture")
    manifest = tmp_path / "identity.json"
    reference_dir = tmp_path / "refs"

    diarization = DiarizationResult(
        "fixture", "SUCCEEDED", (SpeakerTurn("SPEAKER_00", 1.0, 4.0, 0.95),), 1
    )
    extracted = []

    monkeypatch.setattr(pipeline, "run_diarization_command", lambda *args: diarization)
    monkeypatch.setattr(pipeline, "extract_reference_clip", lambda audio, speaker_id, start, end, output_dir: extracted.append((speaker_id, start, end)) or output_dir / "S01.wav")
    monkeypatch.setattr(pipeline, "write_identity_manifest", lambda path, result, identities: None)
    monkeypatch.setattr(manifest, "read_text", lambda encoding="utf-8": '{"characters": [{"character_id": "C01", "speaker_id": "S01", "confidence": 0.95, "reference_audio": "refs/S01.wav", "gender_hint": "unknown"}]}')

    result = pipeline.build_voice_bank(audio, "fixture", manifest, reference_dir)

    assert extracted == [("S01", 1.0, 4.0)]
    assert result["characters"][0]["speaker_id"] == "S01"

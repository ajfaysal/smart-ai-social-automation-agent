import json
from pathlib import Path

from chinese_speaker_pipeline import build_voice_bank
from reference_voice_qc import ReferenceVoiceQC
from speaker_identity import (
    CharacterIdentity,
    DiarizationResult,
    SpeakerTurn,
    character_map,
    normalize_speaker_id,
    write_identity_manifest,
)


def test_normalizes_backend_speaker_labels():
    assert normalize_speaker_id("SPEAKER_00") == "S01"
    assert normalize_speaker_id("SPEAKER_29") == "S30"
    assert normalize_speaker_id("S07") == "S07"


def test_thirty_speaker_fixture_maps_deterministically():
    turns = []
    for i in range(30):
        sid = f"SPEAKER_{i:02d}"
        turns.extend([
            SpeakerTurn(sid, i * 2.0, i * 2.0 + 0.8, 0.96),
            SpeakerTurn(sid, 100 + i * 2.0, 100 + i * 2.0 + 0.7, 0.94),
        ])
    first = character_map(turns)
    second = character_map(list(reversed(turns)))
    assert len(first) == 30
    assert first == second
    assert first["S01"].character_id == "C01"
    assert first["S30"].character_id == "C30"


def test_low_confidence_speaker_is_not_certified():
    turns = [SpeakerTurn("SPEAKER_00", 0, 1, 0.55)]
    assert character_map(turns) == {}


def test_identity_manifest_contains_metadata_only(tmp_path: Path):
    path = tmp_path / "identity.json"
    diarization = DiarizationResult("fixture", "SUCCEEDED", (SpeakerTurn("S01", 0, 1),), 1)
    identities = character_map(diarization.turns)
    write_identity_manifest(path, diarization, identities)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["media_policy"] == "metadata-only-no-reference-audio-committed"
    assert data["characters"][0]["reference_audio"] is None


def test_identity_manifest_records_reference_qc_and_selection_score(tmp_path: Path):
    path = tmp_path / "identity.json"
    diarization = DiarizationResult("fixture", "SUCCEEDED", (SpeakerTurn("S01", 0, 2),), 1)
    qc = ReferenceVoiceQC(
        path="/runtime/S01.wav",
        duration_seconds=2.0,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        silence_ratio=0.1,
        status="SUCCEEDED",
        reason=None,
        selection_score=None,
    )
    identity = CharacterIdentity("C01", "S01", 0.99, "/runtime/S01.wav", "unknown", qc, (2.0, 0.99, 0.0))
    write_identity_manifest(path, diarization, {"S01": identity})
    data = json.loads(path.read_text(encoding="utf-8"))
    character = data["characters"][0]
    assert character["reference_qc"]["status"] == "SUCCEEDED"
    assert character["reference_qc"]["duration_seconds"] == 2.0
    assert character["reference_selection_score"] == [2.0, 0.99, 0.0]


def test_build_voice_bank_persists_reference_evidence(tmp_path: Path, monkeypatch):
    audio = tmp_path / "vocal.wav"
    audio.write_bytes(b"fixture")
    manifest = tmp_path / "identity.json"
    ref = tmp_path / "refs" / "S01.wav"
    ref.parent.mkdir()
    ref.write_bytes(b"fixture")

    diarization = DiarizationResult("fixture", "SUCCEEDED", (SpeakerTurn("SPEAKER_00", 0, 2, 0.95),), 1)
    qc = ReferenceVoiceQC(
        path=str(ref), duration_seconds=2.0, sample_rate=16000, channels=1, sample_width=2,
        silence_ratio=0.1, status="SUCCEEDED", reason=None, selection_score=None,
    )
    monkeypatch.setattr("chinese_speaker_pipeline.run_diarization_command", lambda *_args: diarization)
    monkeypatch.setattr(
        "chinese_speaker_pipeline.extract_best_reference_clips_with_qc",
        lambda *_args, **_kwargs: {"S01": (ref, qc, (2.0, 0.95, 0.0))},
    )
    data = build_voice_bank(audio, "fixture", manifest, ref.parent)
    character = data["characters"][0]
    assert character["reference_audio"] == str(ref)
    assert character["reference_qc"]["status"] == "SUCCEEDED"
    assert character["reference_selection_score"] == [2.0, 0.95, 0.0]

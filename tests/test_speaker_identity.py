import json
from pathlib import Path

from speaker_identity import (
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

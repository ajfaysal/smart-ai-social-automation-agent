from speaker_diarization_contract import build_voice_routes, route_manifest
from speaker_identity import CharacterIdentity, SpeakerTurn


def test_routes_normalize_speaker_labels_and_preserve_character_voice_identity():
    turns = (
        SpeakerTurn("SPEAKER_00", 0, 2, 0.96),
        SpeakerTurn("SPEAKER_01", 2, 4, 0.91),
        SpeakerTurn("SPEAKER_00", 4, 6, 0.95),
    )
    identities = {
        "S01": CharacterIdentity("C01", "S01", 0.955, "/runtime/refs/S01.wav", "female"),
        "S02": CharacterIdentity("C02", "S02", 0.91, "/runtime/refs/S02.wav", "male"),
    }
    routes = build_voice_routes(turns, identities, {"C01": "bn_c01_f_young", "C02": "bn_c02_m_young"})

    assert list(routes) == ["S01", "S02"]
    assert routes["S01"].character_id == "C01"
    assert routes["S01"].voice_profile == "bn_c01_f_young"
    assert routes["S01"].reference_audio.endswith("S01.wav")
    assert route_manifest(routes)[1]["character_id"] == "C02"


def test_low_confidence_identity_is_not_routed():
    turns = (SpeakerTurn("SPEAKER_00", 0, 2, 0.95),)
    identities = {"S01": CharacterIdentity("C01", "S01", 0.69, None)}
    assert build_voice_routes(turns, identities) == {}

from pathlib import Path

from bangla_voice_routing import BanglaVoiceResolver, normalize_gender_hint
from speaker_diarization_contract import build_voice_routes
from speaker_identity import CharacterIdentity, SpeakerTurn


def test_gender_hint_normalization():
    assert normalize_gender_hint("woman") == "female"
    assert normalize_gender_hint("F") == "female"
    assert normalize_gender_hint("father") == "male"
    assert normalize_gender_hint("unknown") == "unknown"


def test_same_character_is_stable_across_repeated_resolution():
    resolver = BanglaVoiceResolver()
    first, source_first = resolver.resolve("C01", "female")
    second, source_second = resolver.resolve("C01", "female")
    assert first == second
    assert source_first == source_second == "native_bangla"


def test_gender_routes_use_distinct_profiles():
    turns = (SpeakerTurn("S01", 0, 2), SpeakerTurn("S02", 2, 4))
    identities = {
        "S01": CharacterIdentity("C01", "S01", 0.95, None, "female"),
        "S02": CharacterIdentity("C02", "S02", 0.95, None, "male"),
    }
    routes = build_voice_routes(turns, identities)
    assert routes["S01"].voice_profile.endswith(("_f_young", "_f_adult", "_f_mature", "_f_soft", "_f_energetic"))
    assert routes["S02"].voice_profile.endswith(("_m_young", "_m_adult", "_m_mature", "_m_deep", "_m_energetic"))
    assert routes["S01"].voice_profile != routes["S02"].voice_profile


def test_configured_profile_wins_without_pitch_rate_variants():
    turns = (SpeakerTurn("S01", 0, 2),)
    identities = {"S01": CharacterIdentity("C01", "S01", 0.95, None, "female")}
    routes = build_voice_routes(turns, identities, {"C01": "bn_c03_f_adult"})
    assert routes["S01"].voice_profile == "bn_c03_f_adult"
    assert routes["S01"].voice_source == "native_bangla"


def test_valid_reference_audio_is_preferred(tmp_path: Path):
    reference = tmp_path / "S01.wav"
    reference.write_bytes(b"reference")
    turns = (SpeakerTurn("S01", 0, 2),)
    identities = {
        "S01": CharacterIdentity("C01", "S01", 0.95, str(reference), "female")
    }
    routes = build_voice_routes(turns, identities)
    assert routes["S01"].reference_audio == str(reference)
    assert routes["S01"].voice_source == "reference_audio"
    assert routes["S01"].voice_profile is not None

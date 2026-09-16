from pathlib import Path

from tts_provider import BANGLA_CHARACTER_PROFILES, bangla_profile_settings, choose_bangla_voice


def test_all_bangla_profiles_resolve_to_supported_neural_bases():
    assert len(BANGLA_CHARACTER_PROFILES) == 10
    for profile, (base, rate, pitch) in BANGLA_CHARACTER_PROFILES.items():
        voice, resolved_rate, resolved_pitch = bangla_profile_settings(profile)
        assert voice.startswith("bn-")
        assert (resolved_rate, resolved_pitch) == (rate, pitch)
        assert choose_bangla_voice(profile).startswith("bn-")


def test_profiles_include_multiple_genders_and_delivery_variants():
    profiles = set(BANGLA_CHARACTER_PROFILES)
    assert any("_f_" in p for p in profiles)
    assert any("_m_" in p for p in profiles)
    assert "bn_c01_f_young" in profiles
    assert "bn_c06_m_mature" in profiles
    assert "bn_c10_m_energetic" in profiles


def test_kaggle_runner_calls_profile_aware_tts():
    source = Path("kaggle_full_pipeline.py").read_text(encoding="utf-8")
    assert "synthesize_bangla(text, Path(out_path), profile=voice)" in source
    assert "drama_dubbing.VOICE_POOL = BANGLA_CHARACTER_VOICE_POOL" in source

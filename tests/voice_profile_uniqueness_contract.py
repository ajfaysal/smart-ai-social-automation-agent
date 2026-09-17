from tts_provider import BANGLA_CHARACTER_PROFILES


def test_bangla_profiles_cover_distinct_base_voice_and_delivery_variants():
    profiles = list(BANGLA_CHARACTER_PROFILES.values())
    assert len(profiles) >= 10
    assert len({p[0] for p in profiles}) >= 4
    assert len({(p[0], p[1], p[2]) for p in profiles}) == len(profiles)

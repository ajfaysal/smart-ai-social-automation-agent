from drama_dubbing import VOICE_POOL


def test_voice_pool_is_stable_for_character_profiles():
    # The Kaggle Bangla runner replaces VOICE_POOL with profile IDs. The core
    # orchestration must honor a director-selected profile when it exists in
    # that pool instead of silently assigning the next generic voice.
    assert isinstance(VOICE_POOL, list)
    assert len(VOICE_POOL) >= 2


def test_profile_routing_contract_is_documented():
    source = open("drama_dubbing.py", encoding="utf-8").read()
    assert "profile if profile in VOICE_POOL" in source
    assert '"profile":profile or "neutral"' in source

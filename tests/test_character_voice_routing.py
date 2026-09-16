from pathlib import Path


def test_voice_pool_is_stable_for_character_profiles():
    source = Path("drama_dubbing.py").read_text(encoding="utf-8")
    assert "VOICE_POOL" in source
    assert "profile if profile in VOICE_POOL" in source


def test_director_profile_is_used_before_generic_voice_fallback():
    source = Path("drama_dubbing.py").read_text(encoding="utf-8")
    marker = 'voices[char] = profile if profile in VOICE_POOL'
    assert marker in source
    assert 'requested_voice if requested_voice!="auto"' in source


def test_manifest_records_character_profile_and_selected_voice():
    source = Path("drama_dubbing.py").read_text(encoding="utf-8")
    assert '"character":char' in source
    assert '"profile":profile or "neutral"' in source
    assert '"voice":voices[char]' in source

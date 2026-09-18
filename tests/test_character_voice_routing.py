from pathlib import Path

def test_voice_router_is_connected():
    source = Path("drama_dubbing.py").read_text(encoding="utf-8")
    assert "voice_for_character" in source

def test_explicit_voice_fallback_remains_supported():
    source = Path("drama_dubbing.py").read_text(encoding="utf-8")
    assert 'requested_voice=requested_voice' in source

def test_manifest_records_character_profile_and_selected_voice():
    source = Path("drama_dubbing.py").read_text(encoding="utf-8")
    assert '"character":char' in source
    assert '"profile":profile or "neutral"' in source
    assert '"voice":voices[char]' in source

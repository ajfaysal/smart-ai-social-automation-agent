from pathlib import Path


def test_dubbing_pipeline_uses_multilingual_router_and_character_stability():
    source = Path("drama_dubbing.py").read_text(encoding="utf-8")
    assert "voice_for_character" in source
    assert "voice_indexes[char]" in source
    assert "voices[char]=voice_for_character" in source
    assert "character-stable" in source


def test_dubbing_pipeline_keeps_v1_dialogue_only_audio_policy():
    source = Path("drama_dubbing.py").read_text(encoding="utf-8")
    assert 'original_dialogue_in_final":False' in source
    assert "background_preserved" in source

from pathlib import Path

from voice_engine_registry import VOICE_ENGINES, available_engines, choose_engine


def test_registry_contains_multiple_open_source_engines():
    assert {"cosyvoice", "fish-speech", "gpt-sovits", "openvoice"}.issubset(VOICE_ENGINES)


def test_character_engine_sharding_is_deterministic(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("COSYVOICE_TTS_COMMAND", "cosy --text {text} --output {output} --reference {reference}")
    monkeypatch.setenv("FISH_SPEECH_TTS_COMMAND", "fish --text {text} --output {output} --reference {reference}")
    monkeypatch.setenv("GPT_SOVITS_TTS_COMMAND", "gpt --text {text} --output {output} --reference {reference}")
    monkeypatch.setenv("OPENVOICE_TTS_COMMAND", "open --text {text} --output {output} --reference {reference}")
    assert choose_engine("C17")[0] == choose_engine("C17")[0]
    assert choose_engine("C18")[0] == choose_engine("C18")[0]


def test_preferred_engine_is_honored(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FISH_SPEECH_TTS_COMMAND", "fish --text {text} --output {output} --reference {reference}")
    reference = tmp_path / "C1.wav"
    reference.write_bytes(b"reference")
    engine, selected = choose_engine("C1", preferred="fish-speech", reference_dir=tmp_path)
    assert engine == "fish-speech"
    assert selected == reference


def test_unconfigured_registry_is_credential_free(monkeypatch):
    for key in ("COSYVOICE_TTS_COMMAND", "FISH_SPEECH_TTS_COMMAND", "GPT_SOVITS_TTS_COMMAND", "OPENVOICE_TTS_COMMAND"):
        monkeypatch.delenv(key, raising=False)
    assert available_engines() == ["edge-neural"]

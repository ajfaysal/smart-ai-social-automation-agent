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


def test_command_engine_renders_acting_directive(monkeypatch, tmp_path: Path):
    import voice_engine_registry
    output = tmp_path / "out.wav"
    reference = tmp_path / "ref.wav"
    reference.write_bytes(b"reference")
    calls = {}
    monkeypatch.setenv(
        "FISH_SPEECH_TTS_COMMAND",
        'fish --text {text} --output {output} --reference {reference} --acting "{acting_directive}"',
    )

    def fake_run(args, check, capture_output, text):
        calls["args"] = args
        calls["check"] = check

    monkeypatch.setattr(voice_engine_registry.subprocess, "run", fake_run)
    output.write_bytes(b"audio")
    voice_engine_registry.run_command_engine(
        "fish-speech", "hello", output, reference, "C1", "sad, whispering"
    )
    assert "--acting" in calls["args"]
    assert calls["args"][calls["args"].index("--acting") + 1] == "sad, whispering"
    assert calls["check"] is True

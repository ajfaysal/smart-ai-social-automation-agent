from pathlib import Path

import pytest

from voice_engine_registry import choose_engine, engine_capability
from tts_provider import synthesize_bangla


def test_reference_required_fails_closed_without_configured_engine(monkeypatch, tmp_path: Path):
    for key in (
        "COSYVOICE_TTS_COMMAND",
        "FISH_SPEECH_TTS_COMMAND",
        "GPT_SOVITS_TTS_COMMAND",
        "OPENVOICE_TTS_COMMAND",
        "BANGLA_REFERENCE_TTS_COMMAND",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("REQUIRE_REFERENCE_VOICE_CLONING", "true")
    with pytest.raises(RuntimeError, match="Reference voice cloning is required"):
        synthesize_bangla("hello", tmp_path / "out.wav", character_id="C1")


def test_reference_required_rejects_missing_reference(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("COSYVOICE_TTS_COMMAND", "cosy --text {text} --output {output} --reference {reference}")
    monkeypatch.setenv("REQUIRE_REFERENCE_VOICE_CLONING", "1")
    with pytest.raises(RuntimeError, match="no reference audio"):
        choose_engine("C1", preferred="cosyvoice", reference_dir=tmp_path, require_reference=True)


def test_reference_required_allows_reference_capable_engine(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("COSYVOICE_TTS_COMMAND", "cosy --text {text} --output {output} --reference {reference}")
    reference = tmp_path / "C1.wav"
    reference.write_bytes(b"reference")
    engine, selected = choose_engine("C1", preferred="cosyvoice", reference_dir=tmp_path, require_reference=True)
    assert engine == "cosyvoice"
    assert selected == reference
    assert engine_capability(engine)["supports_reference_voice"] is True


def test_reference_capability_is_explicit_for_fallback_engine():
    assert engine_capability("edge-neural")["supports_reference_voice"] is False

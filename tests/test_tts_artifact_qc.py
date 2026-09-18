from pathlib import Path
import wave

import pytest

from tts_artifact_qc import validate_tts_artifact


def _wav(path: Path, frames: int = 8000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * frames)


def test_valid_tts_artifact(tmp_path):
    p = tmp_path / "voice.wav"
    _wav(p)
    result = validate_tts_artifact(p)
    assert result["duration_seconds"] == pytest.approx(1.0, abs=0.01)


def test_rejects_missing_artifact(tmp_path):
    with pytest.raises(RuntimeError, match="missing or empty"):
        validate_tts_artifact(tmp_path / "missing.wav")


def test_rejects_non_audio_artifact(tmp_path):
    p = tmp_path / "voice.wav"
    p.write_bytes(b"not audio")
    with pytest.raises(RuntimeError, match="not decodable"):
        validate_tts_artifact(p)


def test_rejects_too_short_audio(tmp_path):
    p = tmp_path / "voice.wav"
    _wav(p, frames=100)
    with pytest.raises(RuntimeError, match="invalid audio/duration"):
        validate_tts_artifact(p, min_duration_seconds=0.05)


def test_bangla_make_tts_uses_reference_aware_provider(monkeypatch, tmp_path):
    import drama_dubbing
    calls = {}
    def fake_synthesize(text, out_path, **kwargs):
        calls.update(kwargs)
    monkeypatch.setattr("tts_provider.synthesize_bangla", fake_synthesize)
    out = tmp_path / "voice.wav"
    drama_dubbing.make_tts("হ্যালো", out, "bn_c01_f_young", "sad", character_id="C01", reference_audio="/runtime/C01.wav", target_language="Bangla")
    assert calls["character_id"] == "C01"
    assert calls["reference_audio"] == "/runtime/C01.wav"


def test_reference_tts_command_receives_acting_directive(monkeypatch, tmp_path):
    import tts_provider
    reference = tmp_path / "C01.wav"
    reference.write_bytes(b"reference")
    calls = {}
    monkeypatch.setenv("BANGLA_REFERENCE_TTS_COMMAND", "echo {acting_directive} {character} {reference} {output}")
    def fake_run(command, shell, check):
        calls["command"] = command
        calls["shell"] = shell
        calls["check"] = check
    monkeypatch.setattr(tts_provider.subprocess, "run", fake_run)
    tts_provider._reference_speak("hello", tmp_path / "out.wav", "C01", str(reference), "sad, whispering")
    assert "sad, whispering" in calls["command"]
    assert "C01" in calls["command"]
    assert calls["shell"] is True
    assert calls["check"] is True


def test_multilingual_make_tts_uses_reference_provider_when_required(monkeypatch, tmp_path):
    import drama_dubbing
    calls = {}
    def fake_synthesize(text, out_path, **kwargs):
        calls.update(kwargs)
    monkeypatch.setenv("REQUIRE_REFERENCE_VOICE_CLONING", "true")
    monkeypatch.setattr("tts_provider.synthesize_reference_tts", fake_synthesize)
    out = tmp_path / "voice.wav"
    drama_dubbing.make_tts("Hello", out, "nova", "sad", character_id="C01", reference_audio="/runtime/C01.wav", target_language="English")
    assert calls["character_id"] == "C01"
    assert calls["target_language"] == "English"
    assert calls["reference_audio"] == "/runtime/C01.wav"

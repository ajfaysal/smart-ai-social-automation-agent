import json

import real_provider_runner


def test_whisper_runner_rejects_empty_segments(monkeypatch, tmp_path):
    audio = tmp_path / "input.wav"
    audio.write_bytes(b"audio")
    monkeypatch.setattr(real_provider_runner, "transcribe", lambda _: {"segments": []})
    try:
        real_provider_runner.run_whisper(audio, tmp_path / "work")
    except RuntimeError as exc:
        assert "segments array" in str(exc)
    else:
        raise AssertionError("expected fail-closed Whisper validation")


def test_xtts_runner_requires_non_empty_text(monkeypatch, tmp_path):
    text = tmp_path / "dialogue.txt"
    reference = tmp_path / "character.wav"
    output = tmp_path / "out.wav"
    text.write_text("", encoding="utf-8")
    reference.write_bytes(b"reference")
    monkeypatch.setattr(real_provider_runner, "reset_provider_executions", lambda: None)
    try:
        real_provider_runner.run_xtts(text, reference, output, "bn")
    except RuntimeError as exc:
        assert "must not be empty" in str(exc)
    else:
        raise AssertionError("expected fail-closed XTTS validation")

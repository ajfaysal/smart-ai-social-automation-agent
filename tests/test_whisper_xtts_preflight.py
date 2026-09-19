import pytest
from real_run_preflight import build_preflight


def test_whisper_xtts_preflight_requires_both_commands(monkeypatch):
    monkeypatch.delenv("WHISPER_LOCAL_COMMAND", raising=False)
    monkeypatch.delenv("XTTS_V2_TTS_COMMAND", raising=False)
    result = build_preflight(
        video_url="https://example.com/drama.mp4",
        require_openai=False,
        require_wav2lip=False,
        require_diarization=False,
        require_whisper_xtts=True,
    )
    assert not result.ready
    assert result.missing_runtime == ("WHISPER_LOCAL_COMMAND", "XTTS_V2_TTS_COMMAND")


def test_whisper_xtts_preflight_accepts_both_commands(monkeypatch):
    monkeypatch.setenv("WHISPER_LOCAL_COMMAND", "whisper --audio {audio} --output {output}")
    monkeypatch.setenv("XTTS_V2_TTS_COMMAND", "xtts --text {text} --output {output} --reference {reference} --language {language}")
    result = build_preflight(
        video_url="https://example.com/drama.mp4",
        require_openai=False,
        require_wav2lip=False,
        require_diarization=False,
        require_whisper_xtts=True,
    )
    assert result.ready

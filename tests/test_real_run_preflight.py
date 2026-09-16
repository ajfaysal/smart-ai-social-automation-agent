import os

import pytest

from real_run_preflight import build_preflight


def test_real_run_defaults_to_chinese_to_bangla(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("WAV2LIP_CHECKPOINT_URL", "https://example.com/wav2lip.pth")
    monkeypatch.setenv("WAV2LIP_S3FD_URL", "https://example.com/s3fd.pth")
    result = build_preflight(video_url="https://example.com/drama.mp4")
    assert result.selection.source_language == "Chinese (Simplified)"
    assert result.selection.target_language == "Bangla"
    assert result.ready
    assert result.missing_secrets == ()


def test_real_run_rejects_non_chinese_source():
    with pytest.raises(ValueError, match="source must be Chinese"):
        build_preflight(
            video_url="https://example.com/drama.mp4",
            source_language="English",
            target_language="Bangla",
            require_openai=False,
            require_wav2lip=False,
        )


def test_real_run_reports_missing_runtime_secrets(monkeypatch):
    for key in ("OPENAI_API_KEY", "WAV2LIP_CHECKPOINT_URL", "WAV2LIP_S3FD_URL"):
        monkeypatch.delenv(key, raising=False)
    result = build_preflight(video_url="https://example.com/drama.mp4")
    assert not result.ready
    assert result.missing_secrets == (
        "OPENAI_API_KEY",
        "WAV2LIP_CHECKPOINT_URL",
        "WAV2LIP_S3FD_URL",
    )


def test_real_run_accepts_no_secret_mode_for_local_validation():
    result = build_preflight(
        video_url="https://example.com/drama.mp4",
        target_language="Hindi",
        require_openai=False,
        require_wav2lip=False,
    )
    assert result.ready
    assert result.selection.target_language == "Hindi"

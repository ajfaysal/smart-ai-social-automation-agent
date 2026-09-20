import pytest

from real_run_preflight import build_preflight, selected_text_provider


@pytest.mark.parametrize(
    ("provider", "key_name"),
    [("openai", "OPENAI_API_KEY"), ("gemini", "GEMINI_API_KEY")],
)
def test_preflight_requires_selected_text_provider_key(monkeypatch, provider, key_name):
    monkeypatch.setenv("DUBBING_TEXT_PROVIDER", provider)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = build_preflight(
        video_url="https://example.com/video.mp4",
        require_wav2lip=False,
        require_diarization=False,
    )
    assert result.missing_secrets == (key_name,)


def test_gemini_key_satisfies_gemini_preflight(monkeypatch):
    monkeypatch.setenv("DUBBING_TEXT_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = build_preflight(
        video_url="https://example.com/video.mp4",
        require_wav2lip=False,
        require_diarization=False,
    )
    assert result.missing_secrets == ()


def test_unknown_text_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("DUBBING_TEXT_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="Unsupported DUBBING_TEXT_PROVIDER"):
        selected_text_provider()

import os


def test_mouth_landmark_provider_prefers_canonical_env(monkeypatch):
    monkeypatch.setenv("MOUTH_LANDMARK_PROVIDER", "mediapipe")
    monkeypatch.setenv("LANDMARK_PROVIDER", "disabled")
    from landmark_provider import get_landmark_provider

    assert get_landmark_provider().name == "mediapipe"


def test_landmark_provider_compatibility_fallback(monkeypatch):
    monkeypatch.delenv("MOUTH_LANDMARK_PROVIDER", raising=False)
    monkeypatch.setenv("LANDMARK_PROVIDER", "mediapipe")
    from landmark_provider import get_landmark_provider

    assert get_landmark_provider().name == "mediapipe"


def test_default_landmark_provider_is_disabled(monkeypatch):
    monkeypatch.delenv("MOUTH_LANDMARK_PROVIDER", raising=False)
    monkeypatch.delenv("LANDMARK_PROVIDER", raising=False)
    from landmark_provider import get_landmark_provider

    assert get_landmark_provider().name == "disabled"

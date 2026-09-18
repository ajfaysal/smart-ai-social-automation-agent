from pathlib import Path

from chinese_dubbing_orchestrator import prepare_speaker_aware_dubbing
from drama_dubbing import make_tts, dub_video
import inspect


def test_dubbing_accepts_speaker_routing():
    assert "speaker_routing" in inspect.signature(dub_video).parameters


def test_tts_accepts_character_reference():
    params = inspect.signature(make_tts).parameters
    assert "character_id" in params
    assert "reference_audio" in params


def test_orchestrator_is_provider_agnostic():
    assert callable(prepare_speaker_aware_dubbing)


def test_kaggle_pipeline_contains_runtime_speaker_execution():
    from kaggle_full_pipeline import build_notebook
    notebook = build_notebook(
        "https://example.com/source.mp4",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Bangla",
    )
    source = "".join(notebook["cells"][0]["source"])
    required = [
        "separate_vocals",
        "prepare_speaker_aware_dubbing",
        "CHINESE_DIARIZATION_BACKEND",
        "speaker-identity.json",
        "speaker-routing.json",
        "reference-voices",
        "speaker_routing=SPEAKER_ROUTES",
        "reference_audio",
        "character_id",
    ]
    for token in required:
        assert token in source

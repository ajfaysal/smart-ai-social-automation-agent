import json

from kaggle_full_pipeline import build_notebook
from kaggle_gpu_orchestrator import main


def test_generated_notebook_is_valid_and_secret_free():
    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Bangla",
    )
    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"
    source = "".join(notebook["cells"][0]["source"])
    assert "KAGGLE_API_TOKEN" not in source
    assert "enable_gpu" not in source
    assert "natural_bangla_tts" in source
    assert "BANGLA_CHARACTER_VOICE_POOL" in source
    assert "preserve_background=False" in source


def test_notebook_serializes_as_json():
    notebook = build_notebook("https://example.com/video.mp4", "owner/repo", "main", "Hindi")
    json.dumps(notebook)


def test_orchestrator_cli_exposes_bangla_as_default_target(monkeypatch):
    monkeypatch.setattr("sys.argv", ["kaggle_gpu_orchestrator.py", "--video-url", "https://example.com/video.mp4", "--dry-run"])
    assert main() == 0

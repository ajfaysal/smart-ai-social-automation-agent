import json

from kaggle_gpu_orchestrator import build_notebook


def test_generated_notebook_is_valid_and_secret_free():
    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "full",
    )
    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"
    source = "".join(notebook["cells"][0]["source"])
    assert "KAGGLE_API_TOKEN" not in source
    assert "enable_gpu" not in source
    assert "run_cloud_smoke.py" in source
    assert "real_provider_runner.py" in source


def test_notebook_serializes_as_json():
    notebook = build_notebook("https://example.com/video.mp4", "owner/repo", "main", "demucs")
    json.dumps(notebook)

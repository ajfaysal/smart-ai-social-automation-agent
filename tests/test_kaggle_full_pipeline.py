import json

from kaggle_full_pipeline import build_notebook


def test_full_notebook_is_secret_free_and_uses_canonical_pipeline():
    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Chinese (Simplified)",
    )
    source = "".join(notebook["cells"][0]["source"])
    assert notebook["nbformat"] == 4
    assert "UserSecretsClient" in source
    assert "OPENAI_API_KEY" in source
    assert "WAV2LIP_CHECKPOINT_URL" in source
    assert "WAV2LIP_S3FD_URL" in source
    assert "dub_video(" in source
    assert "preserve_background=True" in source
    assert "lip_sync=True" in source
    assert "KAGGLE_API_TOKEN" not in source
    json.dumps(notebook)

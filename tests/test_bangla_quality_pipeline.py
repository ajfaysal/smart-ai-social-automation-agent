import json

from kaggle_full_pipeline import build_notebook


def test_bangla_notebook_uses_neural_voice_and_sidechain_mix():
    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Bangla",
    )
    source = "".join(notebook["cells"][0]["source"])
    assert "edge-tts" in source or "edge_neural" in source
    assert "synthesize_bangla" in source
    assert "sidechaincompress" in source
    assert "lip_sync=True" in source
    assert "preserve_background=True" in source
    assert "KAGGLE_API_TOKEN" not in source
    json.dumps(notebook)

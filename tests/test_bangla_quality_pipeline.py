import json

from kaggle_full_pipeline import build_notebook


def test_bangla_notebook_uses_profile_aware_neural_voice_and_replacement_mix():
    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Bangla",
    )
    source = "".join(notebook["cells"][0]["source"])
    assert "synthesize_bangla" in source
    assert "natural_bangla_tts" in source
    assert "BANGLA_CHARACTER_VOICE_POOL" in source
    assert "bangla_director_plan" in source
    assert "drama_dubbing.director_plan = bangla_director_plan" in source
    assert "preserve_background=False" in source
    assert "add_mood_music=False" in source
    assert "replacement-dialogue-only-no-original-music" in source
    assert "lip_sync=True" in source
    assert "KAGGLE_API_TOKEN" not in source
    json.dumps(notebook)

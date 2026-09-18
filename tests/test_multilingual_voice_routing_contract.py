from kaggle_full_pipeline import build_notebook


def test_v1_multilingual_notebook_keeps_target_language_voice_route():
    for language in ("English", "Hindi"):
        notebook = build_notebook("https://example.com/source.mp4", "ajfaysal/smart-ai-social-automation-agent", "main", language)
        source = "".join(notebook["cells"][0]["source"])
        assert "voice_for_character" in source or "VOICE_POOL" in source
        assert language in source
        assert "preserve_background=False" in source
        assert "add_mood_music=False" in source

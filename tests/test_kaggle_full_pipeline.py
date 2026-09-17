    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Bangla",
    )
    source = "".join(notebook["cells"][0]["source"])
    assert "edge-tts" in source
    assert "synthesize_bangla" in source
    assert "natural_bangla_tts" in source
    assert "replacement-dialogue-only-no-original-music" in source
    assert "BANGLA_CHARACTER_VOICE_POOL" in source
    assert source.count("bn_c") >= 10
    assert "preserve_background=False" in source
    assert "add_mood_music=False" in source
    assert "lip_sync=True" in source
    assert "KAGGLE_API_TOKEN" not in source
    json.dumps(notebook)


def test_v1_audio_policy_requires_dialogue_and_music_replacement():

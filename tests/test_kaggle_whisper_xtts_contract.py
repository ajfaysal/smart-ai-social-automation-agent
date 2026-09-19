from kaggle_full_pipeline import build_notebook


def test_kaggle_v1_pins_whisper_large_v3_and_xtts_v2():
    source = "".join(build_notebook("https://example.com/source.mp4", "ajfaysal/smart-ai-social-automation-agent", "main", "Bangla")["cells"][0]["source"])
    assert "DUBBING_STT_PROVIDER'] = 'local-whisper'" in source
    assert "DUBBING_STT_MODEL'] = 'large-v3'" in source
    assert "WHISPER_LOCAL_COMMAND" in source
    assert "XTTS_V2_TTS_COMMAND" in source
    assert "preferred_engine='xtts-v2'" in source
    assert "stt_provider': 'whisper-large-v3'" in source
    assert "tts_provider': 'xtts-v2'" in source

from kaggle_full_pipeline import build_notebook


def test_kaggle_pipeline_cleans_video_before_dubbing():
    notebook = build_notebook("https://example.com/source.mp4", "ajfaysal/smart-ai-social-automation-agent", "main", "Bangla")
    source = "".join(notebook["cells"][0]["source"])
    assert "video_text_cleaner" in source
    assert "clean_video" in source
    assert "cleaned-video.mp4" in source
    assert "text-cleanup.json" in source
    assert "cleaned-with-audio.mp4" in source
    assert source.index("clean_video") < source.index("dub_video")
    assert "preserve_background=False" in source
    assert "add_mood_music=False" in source


def test_kaggle_pipeline_runs_strict_preflight_inside_runtime():
    notebook = build_notebook("https://example.com/source.mp4", "ajfaysal/smart-ai-social-automation-agent", "main", "Hindi")
    source = "".join(notebook["cells"][0]["source"])
    assert "from real_run_preflight import build_preflight" in source
    assert "_preflight = build_preflight" in source
    assert "CHINESE_DIARIZATION_BACKEND" in source
    assert "PYANNOTE_DIARIZATION_COMMAND" in source
    assert "THREE_D_SPEAKER_DIARIZATION_COMMAND" in source
    assert "status':'failed_closed" in source

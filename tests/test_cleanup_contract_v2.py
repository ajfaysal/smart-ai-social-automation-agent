from kaggle_full_pipeline import build_notebook


def test_cleanup_precedes_dubbing():
    source = "".join(build_notebook("https://example.com/source.mp4", "ajfaysal/smart-ai-social-automation-agent", "main", "Bangla")["cells"][0]["source"])
    assert "video_text_cleaner" in source
    assert "clean_video" in source
    assert "cleaned-video.mp4" in source
    assert "text-cleanup.json" in source
    assert "cleaned-with-audio.mp4" in source
    assert source.index("clean_video") < source.index("dub_video")

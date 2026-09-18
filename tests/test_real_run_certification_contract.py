from kaggle_full_pipeline import build_notebook

def test_notebook_has_strict_certification_gate():
    nb=build_notebook("https://example.com/source.mp4","ajfaysal/smart-ai-social-automation-agent","main","Bangla")
    source="".join(nb["cells"][0]["source"])
    assert "real_run_certification" in source
    assert "certification_errors" in source
    assert "failed_closed" in source
    assert "lip-sync was not applied" in source

def test_real_media_runbook_exists():
    from pathlib import Path
    assert Path("REAL_MEDIA_VALIDATION_RUNBOOK.md").exists()

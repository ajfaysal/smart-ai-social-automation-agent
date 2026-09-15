def test_validation_status_exists():
    from pathlib import Path
    assert Path("REAL_MEDIA_VALIDATION_STATUS.md").exists()

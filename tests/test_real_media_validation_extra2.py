def test_real_media_validation_module_exists():
    from pathlib import Path
    assert Path("tests/test_real_media_validation.py").exists()

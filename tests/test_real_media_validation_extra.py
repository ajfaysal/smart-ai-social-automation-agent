"""Additional opt-in assertions for the real-media QC profile."""
from pathlib import Path


def test_real_media_profile_is_documented():
    doc = Path("REAL_MEDIA_VALIDATION.md")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "RUN_REAL_MEDIA_VALIDATION" in text
    assert "workflow_dispatch" in text
    assert "80 ms" in text

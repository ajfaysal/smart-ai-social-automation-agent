from pathlib import Path
import json
import pytest
from kaggle_certification_operator import validate_downloaded_artifacts

def test_validate_requires_all_evidence(tmp_path):
    (tmp_path / "certification.json").write_text(json.dumps({"certified": True}), encoding="utf-8")
    (tmp_path / "final.mp4").write_bytes(b"video")
    (tmp_path / "final.json").write_text("{}", encoding="utf-8")
    for name in ("speaker-identity.json", "speaker-routing.json", "text-cleanup.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    result = validate_downloaded_artifacts(tmp_path)
    assert result["certification"]["certified"] is True
    assert len(result["final_video_sha256"]) == 64

def test_validate_rejects_missing_evidence(tmp_path):
    (tmp_path / "certification.json").write_text(json.dumps({"certified": True}), encoding="utf-8")
    (tmp_path / "final.mp4").write_bytes(b"video")
    (tmp_path / "final.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="evidence artifacts"):
        validate_downloaded_artifacts(tmp_path)

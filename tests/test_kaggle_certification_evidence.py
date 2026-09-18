from pathlib import Path
import json

import pytest

from kaggle_certification_operator import validate_downloaded_artifacts


def _write_certified_output(root: Path, output_name: str = "final.mp4") -> None:
    (root / "certification.json").write_text(
        json.dumps({"certified": True}), encoding="utf-8"
    )
    (root / "cloud-provider-certification.json").write_text(
        json.dumps({"status": "certified", "output": f"/kaggle/working/final-artifacts/{output_name}", "output_sha256": "9b1e9c2d4a8e7f6b5c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1", "manifest_filename": f"{Path(output_name).stem}.json"}),
        encoding="utf-8",
    )
    (root / output_name).write_bytes(b"video")
    (root / f"{Path(output_name).stem}.json").write_text("{}", encoding="utf-8")
    for name in ("speaker-identity.json", "speaker-routing.json", "text-cleanup.json"):
        (root / name).write_text("{}", encoding="utf-8")


def test_validate_requires_all_evidence(tmp_path):
    _write_certified_output(tmp_path)
    result = validate_downloaded_artifacts(tmp_path)
    assert result["certification"]["certified"] is True
    assert result["final_video"].endswith("final.mp4")
    assert len(result["final_video_sha256"]) == 64


def test_validate_selects_authoritative_final_output(tmp_path):
    _write_certified_output(tmp_path, "final.mp4")
    (tmp_path / "intermediate.mp4").write_bytes(b"intermediate")
    result = validate_downloaded_artifacts(tmp_path)
    assert result["final_video"].endswith("final.mp4")


def test_validate_rejects_ambiguous_final_output(tmp_path):
    _write_certified_output(tmp_path, "final.mp4")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "final.mp4").write_bytes(b"duplicate")
    with pytest.raises(RuntimeError, match="exactly one MP4"):
        validate_downloaded_artifacts(tmp_path)


def test_validate_rejects_missing_evidence(tmp_path):
    _write_certified_output(tmp_path)
    (tmp_path / "speaker-routing.json").unlink()
    with pytest.raises(RuntimeError, match="evidence artifacts"):
        validate_downloaded_artifacts(tmp_path)


def test_validate_rejects_sha_mismatch(tmp_path):
    _write_certified_output(tmp_path)
    report = json.loads((tmp_path / 'cloud-provider-certification.json').read_text())
    report['output_sha256'] = '0' * 64
    (tmp_path / 'cloud-provider-certification.json').write_text(json.dumps(report))
    with pytest.raises(RuntimeError, match='SHA-256'):
        validate_downloaded_artifacts(tmp_path)


def test_validate_rejects_missing_authoritative_report(tmp_path):
    _write_certified_output(tmp_path)
    (tmp_path / "cloud-provider-certification.json").unlink()
    with pytest.raises(RuntimeError, match="cloud-provider-certification"):
        validate_downloaded_artifacts(tmp_path)

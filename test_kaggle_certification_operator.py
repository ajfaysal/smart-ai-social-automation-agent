import json

import pytest

from kaggle_certification_operator import classify_status, validate_downloaded_artifacts


def test_classify_status_distinguishes_terminal_states():
    assert classify_status("Kernel is running") == "running"
    assert classify_status("Kernel completed successfully") == "completed"
    assert classify_status("Kernel failed with error") == "failed"
    assert classify_status("Kernel state is unknown") == "unknown"


def test_validate_downloaded_artifacts_rejects_non_certified_run(tmp_path):
    (tmp_path / "certification.json").write_text(
        json.dumps({"certified": False, "reason": "provider failed"}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="without certification"):
        validate_downloaded_artifacts(tmp_path)


def test_validate_downloaded_artifacts_requires_single_certification_file(tmp_path):
    with pytest.raises(RuntimeError, match="exactly one certification.json"):
        validate_downloaded_artifacts(tmp_path)

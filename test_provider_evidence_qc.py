from pathlib import Path

import pytest

from provider_evidence_qc import ingest_provider_evidence
from provider_runtime import reset_provider_executions, snapshot


def setup_function():
    reset_provider_executions()


@pytest.mark.parametrize("artifact_kind", ["missing", "empty"])
def test_succeeded_evidence_with_invalid_artifact_does_not_mutate_runtime(tmp_path: Path, artifact_kind: str):
    artifact = tmp_path / "result.wav"
    if artifact_kind == "empty":
        artifact.write_bytes(b"")

    before = snapshot()
    with pytest.raises(RuntimeError, match="artifact is missing or empty"):
        ingest_provider_evidence({"tts": {"state": "succeeded", "artifact": str(artifact)}})

    assert snapshot() == before


def test_later_malformed_entry_does_not_commit_earlier_valid_evidence():
    before = snapshot()
    evidence = {
        "demucs": {"state": "configured"},
        "tts": {"state": "not-a-real-state"},
    }

    with pytest.raises(RuntimeError, match="state must be one of"):
        ingest_provider_evidence(evidence)

    assert snapshot() == before


def test_valid_evidence_is_committed_after_full_validation():
    ingest_provider_evidence({"demucs": {"state": "configured"}, "tts": {"state": "skipped"}})

    current = snapshot()
    assert current["demucs"]["state"] == "configured"
    assert current["tts"]["state"] == "skipped"

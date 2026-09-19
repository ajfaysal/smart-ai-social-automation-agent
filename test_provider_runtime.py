from pathlib import Path

from provider_reliability import ProviderState
from provider_runtime import finalize, reset_provider_executions, snapshot, validate_artifact


def setup_function():
    reset_provider_executions()


def test_missing_artifact_fails_closed(tmp_path: Path):
    result = finalize("demucs", configured=True, attempted=True,
                      artifact=tmp_path / "missing.wav", suffix=".wav")
    assert result.state is ProviderState.FAILED
    assert result.applied is False
    assert "artifact_missing" in result.reason


def test_valid_artifact_succeeds_and_is_auditable(tmp_path: Path):
    artifact = tmp_path / "background.wav"
    artifact.write_bytes(b"valid-audio" * 200)
    result = finalize("demucs", configured=True, attempted=True,
                      artifact=artifact, min_bytes=16, suffix=".wav",
                      capabilities=["source_separation"])
    assert result.state is ProviderState.SUCCEEDED
    assert result.applied is True
    assert snapshot()["demucs"]["state"] == "succeeded"
    assert snapshot()["demucs"]["applied"] is True


def test_configured_but_not_attempted_is_not_success():
    result = finalize("wav2lip", configured=True, attempted=False,
                      reason="manual_execution_not_started")
    assert result.state is ProviderState.CONFIGURED
    assert result.applied is False


def test_artifact_validation_rejects_wrong_suffix(tmp_path: Path):
    artifact = tmp_path / "render.mov"
    artifact.write_bytes(b"x" * 100)
    ok, reason = validate_artifact(artifact, suffix=".mp4")
    assert ok is False
    assert reason == "artifact_suffix_mismatch:.mov"


def test_provider_audit_contexts_are_isolated():
    from contextvars import copy_context

    reset_provider_executions()
    finalize("parent", configured=True, attempted=False)

    child = copy_context()

    def run_child():
        reset_provider_executions()
        finalize("child", configured=True, attempted=False)
        return snapshot()

    child_snapshot = child.run(run_child)

    assert child_snapshot == {
        "child": {
            "state": "configured",
            "applied": False,
            "reason": "provider_not_attempted",
            "version": None,
            "capabilities": [],
        }
    }
    assert snapshot() == {
        "parent": {
            "state": "configured",
            "applied": False,
            "reason": "provider_not_attempted",
            "version": None,
            "capabilities": [],
        }
    }


def test_record_does_not_mutate_parent_context_dict():
    reset_provider_executions()
    finalize("first", configured=True, attempted=False)

    before = snapshot()
    finalize("second", configured=True, attempted=False)

    assert snapshot() == {
        **before,
        "second": {
            "state": "configured",
            "applied": False,
            "reason": "provider_not_attempted",
            "version": None,
            "capabilities": [],
        },
    }

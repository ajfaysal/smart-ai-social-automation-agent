import asyncio
from pathlib import Path

from provider_reliability import ProviderState
from provider_runtime import (
    finalize,
    reset_provider_executions,
    skip_provider,
    snapshot,
    validate_artifact,
    validate_provider_snapshot,
)


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


def test_skipped_provider_is_explicit_and_not_applied():
    result = skip_provider("wav2lip", "shot_not_eligible_for_lip_sync")
    assert result.state is ProviderState.SKIPPED
    assert result.applied is False
    assert snapshot()["wav2lip"]["reason"] == "shot_not_eligible_for_lip_sync"


def test_invalid_audit_schema_is_rejected():
    ok, reason = validate_provider_snapshot({
        "wav2lip": {"state": "failed", "applied": True, "reason": "boom"}
    })
    assert ok is False
    assert reason == "applied_without_success:wav2lip"


def test_valid_audit_schema_is_accepted():
    ok, reason = validate_provider_snapshot({
        "demucs": {"state": "succeeded", "applied": True, "reason": "artifact_valid"},
        "wav2lip": {"state": "skipped", "applied": False, "reason": "not_eligible"},
    })
    assert ok is True
    assert reason == "provider_audit_valid"


async def _isolated_snapshot(provider: str, reason: str):
    reset_provider_executions()
    await asyncio.sleep(0)
    skip_provider(provider, reason)
    await asyncio.sleep(0)
    return snapshot()


def test_async_contexts_do_not_leak_provider_audit_state():
    async def run():
        left, right = await asyncio.gather(
            _isolated_snapshot("demucs", "job_a"),
            _isolated_snapshot("wav2lip", "job_b"),
        )
        return left, right

    left, right = asyncio.run(run())
    assert set(left) == {"demucs"}
    assert left["demucs"]["reason"] == "job_a"
    assert set(right) == {"wav2lip"}
    assert right["wav2lip"]["reason"] == "job_b"

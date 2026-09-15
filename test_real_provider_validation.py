from pathlib import Path

import pytest

from real_provider_validation import ArtifactExpectation, finalize_execution, validate_artifact
from provider_reliability import ProviderState


def test_missing_artifact_fails_closed(tmp_path: Path):
    ok, reason = validate_artifact(ArtifactExpectation("demucs", str(tmp_path / "missing.wav"), 10, ".wav"))
    assert not ok
    assert reason.startswith("artifact_missing:")


def test_valid_artifact_is_successful(tmp_path: Path):
    output = tmp_path / "no_vocals.wav"
    output.write_bytes(b"0" * 32)
    result = finalize_execution(
        "demucs", configured=True, attempted=True,
        expectation=ArtifactExpectation("demucs", str(output), 10, ".wav"),
        version="test", capabilities={"two_stems": "true"},
    )
    assert result.state is ProviderState.SUCCEEDED
    assert result.applied is True
    assert result.reason == "artifact_valid"


@pytest.mark.parametrize("configured,attempted,state", [
    (False, False, ProviderState.UNAVAILABLE),
    (True, False, ProviderState.CONFIGURED),
])
def test_not_executed_states_are_not_success(configured, attempted, state):
    result = finalize_execution("wav2lip", configured=configured, attempted=attempted)
    assert result.state is state
    assert result.applied is False


def test_provider_failure_never_applies(tmp_path: Path):
    output = tmp_path / "bad.wav"
    output.write_bytes(b"1")
    result = finalize_execution(
        "demucs", configured=True, attempted=True,
        expectation=ArtifactExpectation("demucs", str(output), 10, ".wav"),
    )
    assert result.state is ProviderState.FAILED
    assert result.applied is False
    assert "artifact_too_small" in result.reason

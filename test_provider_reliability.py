import pytest

from provider_reliability import (
    ProviderState,
    attempted,
    configured,
    failed,
    skipped,
    succeeded,
    unavailable,
)


def test_unavailable_is_never_applied():
    result = unavailable("wav2lip", "model weights are missing")
    assert result.state is ProviderState.UNAVAILABLE
    assert result.applied is False
    assert result.to_manifest()["state"] == "unavailable"


def test_configured_is_not_success():
    result = configured("mediapipe")
    assert result.state is ProviderState.CONFIGURED
    assert result.applied is False


def test_attempted_does_not_claim_success():
    result = attempted("wav2lip")
    assert result.state is ProviderState.ATTEMPTED
    assert result.applied is False


def test_failed_provider_carries_reason_and_is_not_applied():
    result = failed("demucs", "subprocess exited with code 1")
    assert result.state is ProviderState.FAILED
    assert result.applied is False
    assert result.reason.startswith("subprocess")


def test_skipped_provider_is_explicit():
    result = skipped("wav2lip", "lip-sync was not requested")
    assert result.state is ProviderState.SKIPPED
    assert result.applied is False


def test_success_is_the_only_applied_state():
    result = succeeded("wav2lip", version="local", capabilities=["video_audio"])
    manifest = result.to_manifest()
    assert result.state is ProviderState.SUCCEEDED
    assert result.applied is True
    assert manifest["version"] == "local"
    assert manifest["capabilities"] == ["video_audio"]


def test_non_success_applied_flag_is_rejected():
    with pytest.raises(ValueError):
        configured("wav2lip")
        # Constructing through the dataclass is intentionally covered below.
    from provider_reliability import ProviderExecution
    with pytest.raises(ValueError):
        ProviderExecution("wav2lip", ProviderState.FAILED, applied=True)

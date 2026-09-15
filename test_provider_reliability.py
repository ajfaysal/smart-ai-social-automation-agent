import pytest
from provider_reliability import ProviderExecution, ProviderState, attempted, configured, failed, skipped, succeeded, unavailable

def test_unavailable_is_not_applied():
    r = unavailable("wav2lip", "model weights are missing")
    assert r.state is ProviderState.UNAVAILABLE and not r.applied

def test_configured_and_attempted_are_not_success():
    assert not configured("mediapipe").applied
    assert not attempted("wav2lip").applied

def test_failed_is_not_applied():
    r = failed("demucs", "subprocess exited with code 1")
    assert r.state is ProviderState.FAILED and not r.applied and "code 1" in r.reason

def test_skipped_is_explicit():
    r = skipped("wav2lip", "lip-sync was not requested")
    assert r.state is ProviderState.SKIPPED and not r.applied

def test_success_is_only_applied_state():
    r = succeeded("wav2lip", version="local", capabilities=["video_audio"])
    data = r.to_manifest()
    assert r.state is ProviderState.SUCCEEDED and r.applied
    assert data["state"] == "succeeded" and data["version"] == "local"

def test_non_success_applied_flag_is_rejected():
    with pytest.raises(ValueError):
        ProviderExecution("wav2lip", ProviderState.FAILED, applied=True)

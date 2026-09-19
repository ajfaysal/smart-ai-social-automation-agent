from provider_reliability import failed, skipped, succeeded
from provider_runtime import reset_provider_executions, record, snapshot, summarize_provider_executions


def test_provider_summary_counts_terminal_states():
    reset_provider_executions()
    record(skipped("lip_sync", "not requested"))
    record(failed("demucs", "execution failed"))
    record(succeeded("tts", "artifact_valid"))
    summary = summarize_provider_executions()
    assert summary["provider_count"] == 3
    assert summary["state_counts"] == {
        "unavailable": 0,
        "configured": 0,
        "attempted": 0,
        "succeeded": 1,
        "failed": 1,
        "skipped": 1,
    }
    assert summary["terminal_count"] == 3
    assert summary["applied_providers"] == ["tts"]
    assert summary["all_terminal"] is True


def test_provider_summary_detects_non_terminal_state():
    reset_provider_executions()
    record(__import__("provider_reliability").configured("wav2lip"))
    summary = summarize_provider_executions(snapshot())
    assert summary["all_terminal"] is False
    assert summary["terminal_count"] == 0

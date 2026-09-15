from provider_audit_qc import provider_audit_qc, validate_provider_audit


def test_applied_requires_success():
    valid, errors = validate_provider_audit({"demucs": {"state": "failed", "applied": True, "reason": "boom"}})
    assert not valid
    assert "demucs:applied_requires_succeeded" in errors


def test_failure_requires_reason():
    valid, errors = validate_provider_audit({"demucs": {"state": "failed", "applied": False}})
    assert not valid
    assert "demucs:terminal_non_success_requires_reason" in errors


def test_valid_success_and_skipped():
    snapshot = {
        "demucs": {"state": "succeeded", "applied": True, "reason": "artifact_valid"},
        "wav2lip": {"state": "skipped", "applied": False, "reason": "not_requested"},
    }
    assert validate_provider_audit(snapshot) == (True, [])
    assert provider_audit_qc(snapshot)["valid"] is True

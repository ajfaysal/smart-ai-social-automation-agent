from pathlib import Path

import demucs_provider
from provider_reliability import ProviderState
from provider_runtime import reset_provider_executions, snapshot


def setup_function():
    reset_provider_executions()


def test_unavailable_demucs_fails_closed(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(demucs_provider.shutil, "which", lambda _: None)
    try:
        demucs_provider.separate(tmp_path / "source.wav", tmp_path)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected Demucs to fail when unavailable")
    assert snapshot()["demucs"]["state"] == ProviderState.UNAVAILABLE.value
    assert snapshot()["demucs"]["applied"] is False


def test_invalid_demucs_artifact_fails_closed(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(demucs_provider.shutil, "which", lambda _: "demucs")
    monkeypatch.setattr(demucs_provider.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 0, "stderr": ""})())
    (tmp_path / "separated").mkdir()
    # Wrong filename: completion without the required background artifact.
    (tmp_path / "separated" / "vocals.wav").write_bytes(b"x" * 2048)
    try:
        demucs_provider.separate(tmp_path / "source.wav", tmp_path)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected missing no_vocals.wav to fail")
    assert snapshot()["demucs"]["state"] == ProviderState.FAILED.value
    assert snapshot()["demucs"]["applied"] is False


def test_valid_demucs_artifact_succeeds(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(demucs_provider.shutil, "which", lambda _: "demucs")
    monkeypatch.setattr(demucs_provider.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 0, "stderr": ""})())
    (tmp_path / "separated").mkdir()
    expected = tmp_path / "separated" / "no_vocals.wav"
    expected.write_bytes(b"x" * 2048)
    result = demucs_provider.separate(tmp_path / "source.wav", tmp_path)
    assert result == expected
    assert snapshot()["demucs"]["state"] == ProviderState.SUCCEEDED.value
    assert snapshot()["demucs"]["applied"] is True


def test_demucs_execution_failure_is_audited(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(demucs_provider.shutil, "which", lambda _: "demucs")
    monkeypatch.setattr(demucs_provider.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 1, "stderr": "model failure"})())
    try:
        demucs_provider.separate(tmp_path / "source.wav", tmp_path)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected Demucs execution failure")
    assert snapshot()["demucs"]["state"] == ProviderState.FAILED.value
    assert snapshot()["demucs"]["applied"] is False

import pytest
from pathlib import Path

import certification_gate as gate


def manifest(**overrides):
    data = {
        "quality_control": {"status": "pass"},
        "original_dialogue_in_final": False,
        "background_preserved": False,
        "music": {"enabled": False},
        "lip_sync": {"applied": True},
        "shot_qc": {"status": "pass"},
        "segments": [{"character": "C1", "voice": "nova", "reference_audio": "/runtime/C1.wav", "reference_qc": {"status": "SUCCEEDED"}, "reference_selection_score": [2.0, 0.9, -1.0], "timing_lock": True, "routing_status": "SUCCEEDED"}],
        "stt_provider": "local-whisper",
        "tts_provider": "xtts-v2",
        "reference_voice_cloning": True,
        "provider_execution": {
            name: {"state": "succeeded", "applied": True, "reason": "artifact_valid"}
            for name in gate.REQUIRED_PROVIDERS
        },
    }
    data.update(overrides)
    return data


def test_certification_requires_real_provider_evidence(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    result = gate.certify(video, manifest(), target_language="Bangla")
    assert result["certified"] is True


def test_certification_fails_without_lipsync(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    with pytest.raises(RuntimeError, match="lip-sync"):
        gate.certify(video, manifest(lip_sync={"applied": False}), target_language="Bangla")


def test_certification_fails_when_provider_not_applied(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    providers = manifest()["provider_execution"]
    providers["tts"] = {"state": "failed", "applied": False}
    with pytest.raises(RuntimeError, match="tts"):
        gate.certify(video, manifest(provider_execution=providers), target_language="English")


def test_certification_fails_when_provider_evidence_is_malformed(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    providers = manifest()["provider_execution"]
    providers["tts"] = "succeeded"
    with pytest.raises(RuntimeError, match="malformed provider evidence"):
        gate.certify(video, manifest(provider_execution=providers), target_language="English")


@pytest.mark.parametrize(
    ("field", "value"),
    [("state", True), ("applied", 1), ("applied", "true")],
)
def test_certification_rejects_non_strict_provider_types(monkeypatch, tmp_path, field, value):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    providers = manifest()["provider_execution"]
    providers["tts"] = dict(providers["tts"])
    providers["tts"][field] = value
    with pytest.raises(RuntimeError, match="strictly"):
        gate.certify(video, manifest(provider_execution=providers), target_language="English")


@pytest.mark.parametrize("source", ["English", "Chinese"])
def test_certification_rejects_non_chinese_source(monkeypatch, tmp_path, source):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    with pytest.raises(RuntimeError, match="source"):
        gate.certify(video, manifest(), source_language=source, target_language="Hindi")


def test_certification_requires_reference_qc(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    with pytest.raises(RuntimeError, match="reference voice QC"):
        gate.certify(video, manifest(segments=[{"character": "C1", "voice": "nova", "reference_audio": "/runtime/C1.wav", "reference_qc": {"status": "FAILED"}, "reference_selection_score": [2.0, 0.9, -1.0], "timing_lock": True}]), target_language="Bangla")


def test_certification_fails_when_segment_routing_not_succeeded(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    segments = manifest()["segments"]
    segments[0] = dict(segments[0], routing_status="UNAVAILABLE")
    with pytest.raises(RuntimeError, match="speaker routing"):
        gate.certify(video, manifest(segments=segments), target_language="Bangla")


def test_certification_fails_when_provider_artifact_was_not_validated(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    providers = manifest()["provider_execution"]
    providers["tts"] = dict(providers["tts"], reason="provider_ok")
    with pytest.raises(RuntimeError, match="strictly succeeded/applied"):
        gate.certify(video, manifest(provider_execution=providers), target_language="Bangla")


def test_certification_enforces_v1_provider_contract(monkeypatch, tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"real")
    monkeypatch.setattr(gate, "_probe", lambda p: {"duration_seconds": 10.0, "streams": ["audio", "video"]})
    with pytest.raises(RuntimeError, match="STT provider contract"):
        gate.certify(video, manifest(stt_provider="openai"), target_language="Bangla", expected_stt_provider="local-whisper", expected_tts_provider="xtts-v2", require_reference_voice_cloning=True)
    with pytest.raises(RuntimeError, match="TTS provider contract"):
        gate.certify(video, manifest(tts_provider="openai"), target_language="Bangla", expected_stt_provider="local-whisper", expected_tts_provider="xtts-v2", require_reference_voice_cloning=True)
    with pytest.raises(RuntimeError, match="reference voice cloning"):
        gate.certify(video, manifest(reference_voice_cloning=False), target_language="Bangla", expected_stt_provider="local-whisper", expected_tts_provider="xtts-v2", require_reference_voice_cloning=True)
    assert gate.certify(video, manifest(), target_language="Bangla", expected_stt_provider="local-whisper", expected_tts_provider="xtts-v2", require_reference_voice_cloning=True)["certified"] is True

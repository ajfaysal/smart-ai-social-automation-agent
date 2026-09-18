from pathlib import Path


def test_speaker_routing_modules_are_present_and_provider_agnostic():
    assert Path("speaker_identity.py").exists()
    assert Path("speaker_segment_router.py").exists()
    assert Path("speaker_diarization_contract.py").exists()
    assert Path("speaker_routing_manifest.py").exists()


def test_runtime_backends_remain_configured_by_environment():
    source = Path("speaker_identity.py").read_text(encoding="utf-8")
    assert "PYANNOTE_DIARIZATION_COMMAND" in source
    assert "THREE_D_SPEAKER_DIARIZATION_COMMAND" in source
    assert "metadata-only-no-reference-audio-committed" in source

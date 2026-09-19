from cloud_certification_report import build_cloud_report


def test_failed_certification_does_not_assert_success_claims(tmp_path):
    report = build_cloud_report(
        certification={"certified": False, "reason": "QC failed"},
        manifest={"original_dialogue_in_final": False, "lip_sync": {"applied": True}, "reference_voice_cloning": True},
        artifacts={"output": tmp_path / "missing.mp4"},
    )
    assert report["status"] == "failed_closed"
    assert report["artifacts"]["output"] is None
    assert report["claims"]["original_dialogue_removed"] == "unknown"
    assert report["claims"]["lip_sync_applied"] == "not_certified"
    assert report["claims"]["reference_voice_cloning"] == "not_certified"
    assert report["providers"]["stt_adapter"] == "local-whisper"
    assert report["providers"]["stt_model"] == "large-v3"


def test_certified_report_derives_claims_from_manifest_and_existing_artifacts(tmp_path):
    output = tmp_path / "dubbed.mp4"
    output.write_bytes(b"video")
    manifest = {
        "original_dialogue_in_final": False,
        "background_preserved": False,
        "music": {"enabled": False},
        "lip_sync": {"applied": True},
        "quality_control": {"status": "pass"},
        "reference_voice_cloning": True,
        "segments": [{"character": "C1"}],
        "stt_provider": "local-whisper",
        "tts_provider": "xtts-v2",
    }
    report = build_cloud_report(
        certification={"certified": True, "artifact_sha256": "abc"},
        manifest=manifest,
        artifacts={"output": output, "subtitle": tmp_path / "missing.srt"},
    )
    assert report["status"] == "certified"
    assert report["artifacts"]["output"] == str(output)
    assert report["artifacts"]["subtitle"] is None
    assert report["claims"]["original_dialogue_removed"] is True
    assert report["claims"]["original_music_removed"] is True
    assert report["claims"]["lip_sync_applied"] is True
    assert report["claims"]["final_qc"] == "pass"
    assert report["claims"]["speaker_routing"] == "validated"
    assert report["providers"]["manifest_stt_provider"] == "local-whisper"
    assert report["providers"]["stt_model"] == "large-v3"

import json

from audio_policy import AudioPolicy, V1_AUDIO_POLICY, describe_policy, validate_policy
from kaggle_full_pipeline import build_evidence_report, build_notebook


def test_full_notebook_is_secret_free_and_uses_canonical_pipeline():
    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Chinese (Simplified)",
    )
    source = "".join(notebook["cells"][0]["source"])
    assert notebook["nbformat"] == 4
    assert "UserSecretsClient" in source
    assert "OPENAI_API_KEY" in source
    assert "REQUIRE_REFERENCE_VOICE_CLONING" in source
    assert "WHISPER_LOCAL_COMMAND" in source
    assert "XTTS_V2_TTS_COMMAND" in source
    assert "DUBBING_STT_PROVIDER" in source
    assert "VOICE_ENGINE_PREFERENCE" in source
    assert "WAV2LIP_CHECKPOINT_URL" in source
    assert "WAV2LIP_S3FD_URL" in source
    assert "dub_video(" in source
    assert "preserve_background=False" in source
    assert "add_mood_music=False" in source
    assert "original_dialogue_removed" in source
    assert "original_music_removed" in source
    assert "KAGGLE_API_TOKEN" not in source
    json.dumps(notebook)


def test_bangla_notebook_uses_neural_multicharacter_voice_pool_and_replacement_mix():
    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Bangla",
    )
    source = "".join(notebook["cells"][0]["source"])
    assert "XTTS_V2_TTS_COMMAND" in source
    assert "DUBBING_STT_MODEL" in source
    assert "synthesize_bangla" in source
    assert "natural_bangla_tts" in source
    assert "acting_directive=None" in source
    assert "acting_directive=acting_directive" in source
    assert "replacement-dialogue-only-no-original-music" in source
    assert "BANGLA_CHARACTER_VOICE_POOL" in source
    assert source.count("bn_c") >= 10
    assert "preserve_background=False" in source
    assert "add_mood_music=False" in source
    assert "lip_sync=True" in source
    assert "KAGGLE_API_TOKEN" not in source
    json.dumps(notebook)


def test_v1_audio_policy_requires_dialogue_and_music_replacement():
    assert describe_policy() == {
        "remove_original_dialogue": True,
        "remove_original_music": True,
        "preserve_original_sfx": False,
    }
    validate_policy(V1_AUDIO_POLICY)


def test_audio_policy_rejects_dialogue_or_music_preservation():
    for policy in (
        AudioPolicy(remove_original_dialogue=False),
        AudioPolicy(remove_original_music=False),
    ):
        try:
            validate_policy(policy)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid V1 audio policy was accepted")


def _report_fixture(tmp_path, certified=True, include_artifacts=True):
    paths = {
        "output": tmp_path / "final.mp4",
        "manifest": tmp_path / "final.json",
        "subtitle": tmp_path / "final.srt",
        "text_cleanup_report": tmp_path / "text-cleanup.json",
        "speaker_identity_manifest": tmp_path / "speaker-identity.json",
        "speaker_routing_manifest": tmp_path / "speaker-routing.json",
    }
    if include_artifacts:
        for path in paths.values():
            path.write_text("artifact", encoding="utf-8")
    certification = {"certified": certified, "reason": None if certified else "provider mismatch"}
    evidence = {
        "speaker_identity_status": "SUCCEEDED",
        "speaker_count": 3,
        "mood": "dramatic",
        "lip_sync": {"applied": True},
        "voice_engine": "xtts-v2-reference-cloned",
        "character_voice_profiles": ["bn_c01_f_young"],
        "audio_mix": "replacement-dialogue-only-no-original-music",
        "original_dialogue_in_final": False,
        "music": {"enabled": False},
        "source_text_cleanup": "ocr-guided-easyocr-opencv-inpaint",
        "speaker_routing": "diarized-speaker-to-character-to-voice-profile/reference-audio",
        "stt_provider": "local-whisper",
        "stt_model": "large-v3",
        "tts_provider": "xtts-v2",
    }
    return build_evidence_report(
        certification, evidence, paths, "sha256" if certified else None,
        identity_payload={"identity": {"status": "SUCCEEDED", "speaker_count": 3}},
        language="Bangla", mood="dramatic", lip=True,
    )


def test_generated_notebook_embeds_evidence_report_contract():
    notebook = build_notebook("https://example.test/video.mp4", "ajfaysal/smart-ai-social-automation-agent", "main", "Bangla")
    source = "".join(notebook["cells"][0]["source"])
    assert "def build_evidence_report(" in source
    assert "manifest_evidence = {}" in source
    assert "Path(value)" in source
    assert "'stt_provider': 'whisper-large-v3'" not in source
    assert "stt_model" in source


def test_evidence_report_certified_is_derived_from_manifest(tmp_path):
    report = _report_fixture(tmp_path, certified=True)
    assert report["status"] == "certified"
    assert report["output"] is not None
    assert report["stt_provider"] == "local-whisper"
    assert report["stt_model"] == "large-v3"
    assert report["tts_provider"] == "xtts-v2"
    assert report["original_dialogue_removed"] is True
    assert report["original_music_removed"] is True


def test_evidence_report_failed_marks_evidence_dependent_claims_unknown(tmp_path):
    report = _report_fixture(tmp_path, certified=False)
    assert report["status"] == "failed_closed"
    assert report["stt_provider"] == "unknown"
    assert report["tts_provider"] == "unknown"
    assert report["original_dialogue_removed"] == "unknown"
    assert report["speaker_count"] == "unknown"


def test_evidence_report_missing_artifacts_does_not_report_paths(tmp_path):
    report = _report_fixture(tmp_path, certified=True, include_artifacts=False)
    assert report["status"] == "certified"
    assert report["output"] is None
    assert report["manifest"] is None
    assert report["subtitle"] is None
    assert report["speaker_identity_manifest"] is None


def test_evidence_report_provider_mismatch_is_not_certified(tmp_path):
    report = _report_fixture(tmp_path, certified=False)
    report["certification"]["reason"] = "certification failed: STT provider contract mismatch: expected local-whisper"
    assert report["status"] == "failed_closed"
    assert report["stt_provider"] == "unknown"
    assert "provider contract mismatch" in report["certification"]["reason"]

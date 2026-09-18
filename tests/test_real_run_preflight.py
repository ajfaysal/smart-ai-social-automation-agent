import pytest
from real_run_preflight import build_preflight

def test_real_run_defaults_to_chinese_to_bangla(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","test")
    monkeypatch.setenv("WAV2LIP_CHECKPOINT_URL","https://example.com/wav2lip.pth")
    monkeypatch.setenv("WAV2LIP_S3FD_URL","https://example.com/s3fd.pth")
    monkeypatch.setenv("PYANNOTE_DIARIZATION_COMMAND","python diarize.py --audio {audio} --output {output}")
    result=build_preflight(video_url="https://example.com/drama.mp4")
    assert result.ready

def test_real_run_rejects_non_chinese_source():
    with pytest.raises(ValueError,match="source must be Chinese"):
        build_preflight(video_url="https://example.com/drama.mp4",source_language="English",target_language="Bangla",require_openai=False,require_wav2lip=False,require_diarization=False)

def test_real_run_reports_missing_runtime_prerequisites(monkeypatch):
    for key in ("OPENAI_API_KEY","WAV2LIP_CHECKPOINT_URL","WAV2LIP_S3FD_URL","PYANNOTE_DIARIZATION_COMMAND"):
        monkeypatch.delenv(key,raising=False)
    result=build_preflight(video_url="https://example.com/drama.mp4")
    assert not result.ready
    assert result.missing_secrets==("OPENAI_API_KEY","WAV2LIP_CHECKPOINT_URL","WAV2LIP_S3FD_URL")
    assert result.missing_runtime==("PYANNOTE_DIARIZATION_COMMAND",)

def test_real_run_accepts_no_secret_mode_for_local_validation():
    result=build_preflight(video_url="https://example.com/drama.mp4",target_language="Hindi",require_openai=False,require_wav2lip=False,require_diarization=False)
    assert result.ready
    assert result.selection.target_language=="Hindi"

def test_3d_speaker_backend_requires_its_runtime_command(monkeypatch):
    monkeypatch.delenv("THREE_D_SPEAKER_DIARIZATION_COMMAND",raising=False)
    result=build_preflight(video_url="https://example.com/drama.mp4",require_openai=False,require_wav2lip=False,diarization_backend="3d-speaker")
    assert not result.ready
    assert result.missing_runtime==("THREE_D_SPEAKER_DIARIZATION_COMMAND",)


def test_kaggle_notebook_requires_selected_diarization_runtime_secret():
    from kaggle_full_pipeline import build_notebook
    notebook = build_notebook("https://example.com/drama.mp4", "ajfaysal/smart-ai-social-automation-agent", "main", "Bangla")
    source = "".join(notebook["cells"][0]["source"])
    assert "PYANNOTE_DIARIZATION_COMMAND" in source
    assert "secret(_diarization_secret, required=True)" in source


def test_kaggle_notebook_supports_3d_speaker_runtime_contract():
    from kaggle_full_pipeline import build_notebook
    notebook = build_notebook("https://example.com/drama.mp4", "ajfaysal/smart-ai-social-automation-agent", "main", "Hindi")
    source = "".join(notebook["cells"][0]["source"])
    assert "THREE_D_SPEAKER_DIARIZATION_COMMAND" in source


def test_reference_voice_preflight_requires_a_reference_tts_engine(monkeypatch):
    for key in ("BANGLA_REFERENCE_TTS_COMMAND","COSYVOICE_TTS_COMMAND","FISH_SPEECH_TTS_COMMAND","GPT_SOVITS_TTS_COMMAND","OPENVOICE_TTS_COMMAND"):
        monkeypatch.delenv(key, raising=False)
    result=build_preflight(video_url="https://example.com/drama.mp4", require_openai=False, require_wav2lip=False, require_diarization=False, require_reference_voice=True)
    assert not result.ready
    assert "REFERENCE_TTS_ENGINE_COMMAND" in result.missing_runtime


def test_reference_voice_preflight_accepts_configured_engine(monkeypatch):
    monkeypatch.setenv("FISH_SPEECH_TTS_COMMAND", "fish --text {text} --output {output} --reference {reference}")
    result=build_preflight(video_url="https://example.com/drama.mp4", require_openai=False, require_wav2lip=False, require_diarization=False, require_reference_voice=True)
    assert result.ready

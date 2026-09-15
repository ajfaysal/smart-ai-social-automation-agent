from pathlib import Path

import pytest

from provider_media_validation import validate_video_audio


def test_missing_video_fails_closed(tmp_path: Path):
    with pytest.raises(RuntimeError, match="artifact_missing"):
        validate_video_audio(tmp_path / "missing.mp4")


def test_invalid_probe_output_fails_closed(monkeypatch, tmp_path: Path):
    import provider_media_validation as module

    path = tmp_path / "output.mp4"
    path.write_bytes(b"x")
    monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/ffprobe")

    class Completed:
        returncode = 0
        stdout = '{"streams": [{"codec_type": "video"}], "format": {"duration": "1.0"}}'
        stderr = ""

    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: Completed())
    with pytest.raises(RuntimeError, match="audio_stream_missing"):
        validate_video_audio(path)


def test_valid_video_audio_metadata(monkeypatch, tmp_path: Path):
    import provider_media_validation as module

    path = tmp_path / "output.mp4"
    path.write_bytes(b"x")
    monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/ffprobe")

    class Completed:
        returncode = 0
        stdout = '{"streams": [{"codec_type": "video"}, {"codec_type": "audio"}], "format": {"duration": "2.5"}}'
        stderr = ""

    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: Completed())
    result = validate_video_audio(path)
    assert result["validated"] is True
    assert result["duration"] == 2.5
    assert result["video_streams"] == 1
    assert result["audio_streams"] == 1

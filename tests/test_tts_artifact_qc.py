from pathlib import Path
import wave

import pytest

from tts_artifact_qc import validate_tts_artifact


def _wav(path: Path, frames: int = 8000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * frames)


def test_valid_tts_artifact(tmp_path):
    p = tmp_path / "voice.wav"
    _wav(p)
    result = validate_tts_artifact(p)
    assert result["duration_seconds"] == pytest.approx(1.0, abs=0.01)


def test_rejects_missing_artifact(tmp_path):
    with pytest.raises(RuntimeError, match="missing or empty"):
        validate_tts_artifact(tmp_path / "missing.wav")


def test_rejects_non_audio_artifact(tmp_path):
    p = tmp_path / "voice.wav"
    p.write_bytes(b"not audio")
    with pytest.raises(RuntimeError, match="not decodable"):
        validate_tts_artifact(p)


def test_rejects_too_short_audio(tmp_path):
    p = tmp_path / "voice.wav"
    _wav(p, frames=100)
    with pytest.raises(RuntimeError, match="invalid audio/duration"):
        validate_tts_artifact(p, min_duration_seconds=0.05)

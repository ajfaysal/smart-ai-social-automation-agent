import math
import wave
from pathlib import Path

import pytest

from reference_voice_qc import validate_reference_voice


def _wav(path: Path, seconds: float, tone: bool = True):
    rate = 16000
    frames = int(rate * seconds)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        data = bytearray()
        for i in range(frames):
            value = int(5000 * math.sin(2 * math.pi * 220 * i / rate)) if tone else 0
            data.extend(value.to_bytes(2, "little", signed=True))
        w.writeframes(data)


def test_accepts_normalized_reference_voice(tmp_path):
    path = tmp_path / "ref.wav"
    _wav(path, 2.0)
    report = validate_reference_voice(path)
    assert report.status == "SUCCEEDED"
    assert report.sample_rate == 16000
    assert report.channels == 1
    assert report.silence_ratio < 0.65


@pytest.mark.parametrize("seconds", [0.5, 9.0])
def test_rejects_bad_duration(tmp_path, seconds):
    path = tmp_path / "ref.wav"
    _wav(path, seconds)
    with pytest.raises(ValueError):
        validate_reference_voice(path)


def test_rejects_mostly_silent_reference(tmp_path):
    path = tmp_path / "ref.wav"
    _wav(path, 2.0, tone=False)
    with pytest.raises(ValueError, match="mostly silent"):
        validate_reference_voice(path)

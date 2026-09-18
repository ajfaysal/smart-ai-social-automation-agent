import math
import wave
from pathlib import Path

from speaker_identity import SpeakerTurn, extract_best_reference_clips


def _wav(path: Path, seconds: float):
    rate = 8000
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        data = bytearray()
        for i in range(int(rate * seconds)):
            value = int(5000 * math.sin(2 * math.pi * 220 * i / rate))
            data.extend(value.to_bytes(2, "little", signed=True))
        w.writeframes(data)


def test_selects_longest_eligible_turn_per_speaker(tmp_path):
    audio = tmp_path / "vocal.wav"
    _wav(audio, 5)
    refs = extract_best_reference_clips(
        audio,
        [
            SpeakerTurn("SPEAKER_00", 0, 1, 1),
            SpeakerTurn("SPEAKER_00", 1, 4, 1),
            SpeakerTurn("SPEAKER_01", 0, 0.5, 1),
        ],
        tmp_path / "refs",
    )
    assert set(refs) == {"S01"}
    assert refs["S01"].name == "S01.wav"
    assert refs["S01"].exists()


def test_caps_reference_duration(tmp_path):
    audio = tmp_path / "vocal.wav"
    _wav(audio, 12)
    refs = extract_best_reference_clips(
        audio, [SpeakerTurn("S01", 0, 10, 1)], tmp_path / "refs"
    )
    assert refs["S01"].exists()

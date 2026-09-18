import wave
from pathlib import Path

from speaker_identity import SpeakerTurn, extract_best_reference_clips

def _wav(path: Path, seconds: float):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b"\x00\x00" * int(8000 * seconds))

def test_selects_longest_eligible_turn_per_speaker(tmp_path):
    audio=tmp_path/"vocal.wav"; _wav(audio, 5)
    refs=extract_best_reference_clips(
        audio,
        [SpeakerTurn("SPEAKER_00",0,1,1), SpeakerTurn("SPEAKER_00",1,4,1), SpeakerTurn("SPEAKER_01",0,0.5,1)],
        tmp_path/"refs",
    )
    assert set(refs) == {"S01"}
    assert refs["S01"].name == "S01.wav"
    assert refs["S01"].exists()

def test_caps_reference_duration(tmp_path):
    audio=tmp_path/"vocal.wav"; _wav(audio, 12)
    refs=extract_best_reference_clips(audio,[SpeakerTurn("S01",0,10,1)],tmp_path/"refs")
    assert refs["S01"].exists()

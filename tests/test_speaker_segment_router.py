from speaker_identity import SpeakerTurn
from speaker_segment_router import assign_speakers_to_segments


def test_assigns_normalized_speaker_by_maximum_overlap():
    segments = [(0.0, 2.0, "你好"), (2.0, 4.0, "别走")]
    turns = (
        SpeakerTurn("SPEAKER_00", 0.0, 2.1, 0.95),
        SpeakerTurn("SPEAKER_01", 2.1, 4.0, 0.92),
    )
    routed = assign_speakers_to_segments(segments, turns)
    assert routed[0]["speaker_id"] == "S01"
    assert routed[1]["speaker_id"] == "S02"


def test_short_overlap_does_not_force_speaker_identity():
    routed = assign_speakers_to_segments([(0.0, 4.0, "dialogue")], (SpeakerTurn("SPEAKER_00", 3.2, 4.0),))
    assert "speaker_id" not in routed[0]

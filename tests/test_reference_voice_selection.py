from speaker_identity import SpeakerTurn, _reference_score


def test_reference_score_prefers_confidence_when_duration_matches():
    low = SpeakerTurn("S01", 0, 3, 0.75)
    high = SpeakerTurn("S01", 4, 7, 0.95)
    assert _reference_score(None, high, max_seconds=8) > _reference_score(None, low, max_seconds=8)


def test_reference_score_caps_duration():
    turn = SpeakerTurn("S01", 0, 20, 0.8)
    assert _reference_score(None, turn, max_seconds=8)[0] == 8


def test_reference_qc_evidence_helper_exposes_selection_and_qc():
    import speaker_identity
    assert hasattr(speaker_identity, "extract_best_reference_clips_with_qc")

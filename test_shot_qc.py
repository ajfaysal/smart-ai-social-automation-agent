from shot_qc import validate_shot_plan


def test_contiguous_shots():
    shots = [{"index": 0, "start": 0, "end": 2}, {"index": 1, "start": 2, "end": 5}]
    result = validate_shot_plan(shots, 5)
    assert result["status"] == "pass"
    assert result["gaps"] == 0
    assert result["overlaps"] == 0


def test_gap_rejected():
    shots = [{"index": 0, "start": 0, "end": 2}, {"index": 1, "start": 2.2, "end": 5}]
    try:
        validate_shot_plan(shots, 5)
    except RuntimeError as exc:
        assert "gaps" in str(exc)
    else:
        raise AssertionError("Expected shot gap to fail QC")

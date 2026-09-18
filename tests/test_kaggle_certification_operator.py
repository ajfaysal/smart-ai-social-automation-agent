from kaggle_certification_operator import classify_status

def test_classify_running():
    assert classify_status("Status: Running") == "running"

def test_classify_completed():
    assert classify_status("Status: Completed") == "completed"

def test_classify_failed():
    assert classify_status("Status: Error") == "failed"

def test_classify_unknown():
    assert classify_status("Status: Queued for GPU") == "running"

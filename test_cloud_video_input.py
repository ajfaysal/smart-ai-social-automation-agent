from cloud_video_input import google_drive_file_id


def test_drive_file_url_extracts_id():
    assert google_drive_file_id(
        "https://drive.google.com/file/d/1brOpsZOsoM2oWijxbYyHKDlDrsQTnO7-/view?usp=drivesdk"
    ) == "1brOpsZOsoM2oWijxbYyHKDlDrsQTnO7-"


def test_drive_query_url_extracts_id():
    assert google_drive_file_id("https://drive.google.com/open?id=abc_123") == "abc_123"


def test_non_drive_url_returns_none():
    assert google_drive_file_id("https://example.com/video.mp4") is None

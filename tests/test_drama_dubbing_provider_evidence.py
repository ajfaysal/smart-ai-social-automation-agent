import pytest

import drama_dubbing


def test_dub_video_rejects_non_object_provider_evidence(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"not-a-real-video")

    with pytest.raises(RuntimeError, match="Malformed provider evidence"):
        drama_dubbing.dub_video(
            video,
            "Bangla",
            provider_evidence={"diarization": "succeeded"},
        )


def test_dub_video_rejects_success_without_artifact(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"not-a-real-video")

    with pytest.raises(RuntimeError, match="requires an artifact path"):
        drama_dubbing.dub_video(
            video,
            "Bangla",
            provider_evidence={"diarization": {"state": "succeeded"}},
        )

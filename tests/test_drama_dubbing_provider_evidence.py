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


def test_dub_video_rejects_unknown_provider_state(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"not-a-real-video")
    with pytest.raises(RuntimeError, match="state must be one of"):
        drama_dubbing.dub_video(video, "Bangla", provider_evidence={"diarization": {"state": "success"}})


@pytest.mark.parametrize("field", ["configured", "attempted"])
def test_dub_video_rejects_non_boolean_provider_flags(tmp_path, field):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"not-a-real-video")
    evidence = {"state": "failed", field: "true"}
    with pytest.raises(RuntimeError, match=field):
        drama_dubbing.dub_video(video, "Bangla", provider_evidence={"diarization": evidence})


def test_dub_video_rejects_non_string_capabilities(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"not-a-real-video")
    with pytest.raises(RuntimeError, match="capabilities"):
        drama_dubbing.dub_video(
            video, "Bangla",
            provider_evidence={"diarization": {"state": "failed", "capabilities": "diarization"}},
        )


def test_dub_video_rejects_artifact_for_non_success_state(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"not-a-real-video")
    with pytest.raises(RuntimeError, match="artifact is only valid"):
        drama_dubbing.dub_video(
            video, "Bangla",
            provider_evidence={"diarization": {"state": "failed", "artifact": "artifact.json"}},
        )

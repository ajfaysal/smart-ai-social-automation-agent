from speaker_diarization_contract import SpeakerVoiceRoute
from speaker_routing_manifest import build_segment_routes


def test_segment_route_manifest_attaches_character_and_voice_metadata():
    routes = {"S01": SpeakerVoiceRoute("S01", "C01", "bn_c01_f_young", "/runtime/S01.wav", 0.95)}
    routed = build_segment_routes([
        {"index": 0, "start": 0.0, "end": 2.0, "text": "你好", "speaker_id": "S01"},
        {"index": 1, "start": 2.0, "end": 3.0, "text": "未知"},
    ], routes)
    assert routed[0]["character_id"] == "C01"
    assert routed[0]["voice_profile"] == "bn_c01_f_young"
    assert routed[0]["routing_status"] == "SUCCEEDED"
    assert routed[1]["routing_status"] == "UNAVAILABLE"

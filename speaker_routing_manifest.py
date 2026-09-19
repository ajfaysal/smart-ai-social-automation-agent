"""Build an auditable segment-to-character routing manifest."""
from __future__ import annotations

from speaker_diarization_contract import SpeakerVoiceRoute


def build_segment_routes(routed_segments, routes):
    """Attach character/voice metadata to transcript segments without altering media."""
    result = []
    for item in routed_segments:
        sid = item.get("speaker_id")
        route = routes.get(sid) if sid else None
        row = dict(item)
        row["character_id"] = route.character_id if route else None
        row["voice_profile"] = route.voice_profile if route else None
        row["voice_source"] = route.voice_source if route else None
        row["reference_audio"] = route.reference_audio if route else None
        row["reference_qc"] = route.reference_qc if route else None
        row["reference_selection_score"] = route.reference_selection_score if route else None
        row["routing_status"] = "SUCCEEDED" if route else "UNAVAILABLE"
        result.append(row)
    return result

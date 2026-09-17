"""Provider-agnostic orchestration facade for Chinese speaker-aware dubbing."""
from __future__ import annotations

from pathlib import Path

from chinese_speaker_pipeline import build_voice_bank
from speaker_diarization_contract import build_voice_routes, route_manifest
from speaker_segment_router import assign_speakers_to_segments
from speaker_routing_manifest import build_segment_routes


def prepare_speaker_aware_dubbing(audio: Path, transcript_segments, backend: str, identity_manifest: Path, reference_dir: Path | None = None, voice_profiles: dict[str, str] | None = None) -> dict:
    """Run diarization/voice-bank preparation and return an auditable TTS routing payload.

    Model weights, credentials, and reference audio stay runtime-only. This function does
    not synthesize or alter media; it prepares the exact speaker-aware handoff consumed by
    the dubbing stage.
    """
    payload = build_voice_bank(audio, backend, identity_manifest, reference_dir)
    turns = tuple(
        __import__("speaker_identity").SpeakerTurn(str(x["speaker"]), float(x["start"]), float(x["end"]), float(x.get("confidence", 1.0)))
        for x in payload.get("turns", [])
    )
    identities = {
        str(x["speaker_id"]): __import__("speaker_identity").CharacterIdentity(
            str(x["character_id"]), str(x["speaker_id"]), float(x["confidence"]), x.get("reference_audio"), str(x.get("gender_hint", "unknown"))
        )
        for x in payload.get("characters", [])
    }
    routes = build_voice_routes(turns, identities, voice_profiles)
    routed_segments = assign_speakers_to_segments(transcript_segments, turns)
    segments = build_segment_routes(routed_segments, routes)
    return {"identity": payload, "speaker_routes": route_manifest(routes), "segments": segments}

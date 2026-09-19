"""Contract helpers connecting diarized Chinese speakers to dubbing voice routing."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from reference_voice_qc import ReferenceVoiceQC
from speaker_identity import CharacterIdentity, SpeakerTurn, normalize_speaker_id


@dataclass(frozen=True)
class SpeakerVoiceRoute:
    speaker_id: str
    character_id: str
    gender_hint: str
    voice_profile: str | None
    reference_audio: str | None
    reference_qc: ReferenceVoiceQC | None
    reference_selection_score: tuple[float, float, float] | None
    confidence: float


def build_voice_routes(
    turns: Iterable[SpeakerTurn],
    identities: dict[str, CharacterIdentity],
    voice_profiles: dict[str, str] | None = None,
    minimum_confidence: float = 0.70,
) -> dict[str, SpeakerVoiceRoute]:
    """Build a deterministic speaker->character->voice handoff with auditable gender hints."""
    voice_profiles = voice_profiles or {}
    active = {normalize_speaker_id(t.speaker_id) for t in turns}
    routes: dict[str, SpeakerVoiceRoute] = {}
    for sid in sorted(active):
        identity = identities.get(sid)
        if identity is None or identity.confidence < minimum_confidence:
            continue
        routes[sid] = SpeakerVoiceRoute(
            speaker_id=sid,
            character_id=identity.character_id,
            gender_hint=str(identity.gender_hint or "unknown").strip().lower() or "unknown",
            voice_profile=voice_profiles.get(identity.character_id),
            reference_audio=identity.reference_audio,
            reference_qc=identity.reference_qc,
            reference_selection_score=identity.reference_selection_score,
            confidence=identity.confidence,
        )
    return routes


def route_manifest(routes: dict[str, SpeakerVoiceRoute]) -> list[dict]:
    return [asdict(routes[sid]) for sid in sorted(routes)]

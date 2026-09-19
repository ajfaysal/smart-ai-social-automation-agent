"""Contract helpers connecting diarized Chinese speakers to dubbing voice routing."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from bangla_voice_routing import BanglaVoiceResolver
from reference_voice_qc import ReferenceVoiceQC
from speaker_identity import CharacterIdentity, SpeakerTurn, normalize_speaker_id


@dataclass(frozen=True)
class SpeakerVoiceRoute:
    speaker_id: str
    character_id: str
    voice_profile: str | None
    reference_audio: str | None
    reference_qc: ReferenceVoiceQC | None
    reference_selection_score: tuple[float, float, float] | None
    confidence: float
    voice_source: str = "native_bangla"


def build_voice_routes(
    turns: Iterable[SpeakerTurn],
    identities: dict[str, CharacterIdentity],
    voice_profiles: dict[str, str] | None = None,
    minimum_confidence: float = 0.70,
) -> dict[str, SpeakerVoiceRoute]:
    """Build deterministic speaker->character->voice routing with reference fallback."""
    resolver = BanglaVoiceResolver(voice_profiles)
    active = {normalize_speaker_id(t.speaker_id) for t in turns}
    routes: dict[str, SpeakerVoiceRoute] = {}
    for sid in sorted(active):
        identity = identities.get(sid)
        if identity is None or identity.confidence < minimum_confidence:
            continue
        profile, source = resolver.resolve(
            identity.character_id,
            identity.gender_hint,
            identity.reference_audio,
        )
        routes[sid] = SpeakerVoiceRoute(
            speaker_id=sid,
            character_id=identity.character_id,
            voice_profile=profile,
            reference_audio=identity.reference_audio,
            reference_qc=identity.reference_qc,
            reference_selection_score=identity.reference_selection_score,
            confidence=identity.confidence,
            voice_source=source,
        )
    return routes


def route_manifest(routes: dict[str, SpeakerVoiceRoute]) -> list[dict]:
    return [asdict(routes[sid]) for sid in sorted(routes)]

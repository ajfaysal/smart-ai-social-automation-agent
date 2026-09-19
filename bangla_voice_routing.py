"""Deterministic Bangla character voice routing.

Profiles are semantic voice identities, not pitch/rate variants. Runtime reference
audio takes precedence when present; native Bengali profiles are the deterministic
fallback. No voice samples or provider credentials belong in source control.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path


BANGLA_FEMALE_PROFILES = (
    "bn_c01_f_young",
    "bn_c03_f_adult",
    "bn_c05_f_mature",
    "bn_c07_f_soft",
    "bn_c09_f_energetic",
)
BANGLA_MALE_PROFILES = (
    "bn_c02_m_young",
    "bn_c04_m_adult",
    "bn_c06_m_mature",
    "bn_c08_m_deep",
    "bn_c10_m_energetic",
)
BANGLA_UNKNOWN_PROFILES = BANGLA_FEMALE_PROFILES + BANGLA_MALE_PROFILES


def normalize_gender_hint(value: str | None) -> str:
    hint = str(value or "").strip().lower()
    if hint in {"female", "woman", "girl", "mother", "sister", "f"}:
        return "female"
    if hint in {"male", "man", "boy", "father", "brother", "m"}:
        return "male"
    return "unknown"


class BanglaVoiceResolver:
    """Assign one stable native profile per character, without profile reuse by gender."""

    def __init__(self, configured: dict[str, str] | None = None) -> None:
        self.configured = dict(configured or {})
        self._assigned: dict[str, str] = {}
        self._used: dict[str, set[str]] = defaultdict(set)

    def resolve(
        self,
        character_id: str,
        gender_hint: str | None = None,
        reference_audio: str | None = None,
    ) -> tuple[str | None, str]:
        if reference_audio and Path(reference_audio).is_file():
            return self.configured.get(character_id), "reference_audio"

        if character_id in self._assigned:
            return self._assigned[character_id], "native_bangla"

        configured = self.configured.get(character_id)
        if configured:
            self._assigned[character_id] = configured
            return configured, "native_bangla"

        gender = normalize_gender_hint(gender_hint)
        pool = (
            BANGLA_FEMALE_PROFILES if gender == "female"
            else BANGLA_MALE_PROFILES if gender == "male"
            else BANGLA_UNKNOWN_PROFILES
        )
        used = self._used[gender]
        available = [profile for profile in pool if profile not in used]
        profile = available[0] if available else pool[len(self._assigned) % len(pool)]
        self._assigned[character_id] = profile
        used.add(profile)
        return profile, "native_bangla"

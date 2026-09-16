"""V1 product scope for the Chinese-drama dubbing pipeline.

The architecture keeps the wider language registry intact for later releases, but
V1 certification is intentionally limited to Chinese source dramas with one of
three selectable target languages.
"""
from __future__ import annotations

from dataclasses import dataclass

V1_SOURCE_LANGUAGES = frozenset({"Chinese (Simplified)", "Chinese (Traditional)"})
V1_TARGET_LANGUAGES = frozenset({"Bangla", "English", "Hindi"})

@dataclass(frozen=True)
class V1LanguageSelection:
    source_language: str
    target_language: str


def validate_v1_selection(source_language: str, target_language: str) -> V1LanguageSelection:
    source = str(source_language).strip()
    target = str(target_language).strip()
    if source not in V1_SOURCE_LANGUAGES:
        raise ValueError(
            f"V1 source must be Chinese (Simplified) or Chinese (Traditional), got {source!r}."
        )
    if target not in V1_TARGET_LANGUAGES:
        raise ValueError(
            f"V1 target must be Bangla, English, or Hindi, got {target!r}."
        )
    if source == target:
        raise ValueError("V1 certification requires translation into a different language.")
    return V1LanguageSelection(source, target)


def is_v1_target(language: str) -> bool:
    return str(language).strip() in V1_TARGET_LANGUAGES

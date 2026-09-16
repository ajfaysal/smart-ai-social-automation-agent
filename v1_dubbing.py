"""V1 Chinese-drama dubbing contract.

Keeps the existing wider language registry intact while providing one explicit
launch path: Mandarin Chinese drama -> Bangla, English, or Hindi.
"""
from __future__ import annotations

from core_language_config import TARGET_LANGUAGES, validate_target_language

V1_SOURCE_LANGUAGE_NAMES = ("Chinese (Simplified)", "Chinese (Traditional)")
V1_TARGET_LANGUAGE_NAMES = tuple(TARGET_LANGUAGES)


def validate_v1_target(target_language: str) -> str:
    """Validate a selected V1 target and return its canonical code."""
    return validate_target_language(target_language)


def selected_target(target_language: str) -> dict[str, str]:
    """Return UI/API metadata for the selected V1 target."""
    code = validate_target_language(target_language)
    return {"label": target_language, "code": code, "source": "zh"}

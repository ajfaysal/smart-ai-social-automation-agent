"""V1 language contract: Mandarin Chinese drama -> Bangla/English/Hindi.

The wider language registry remains elsewhere for future development; this module
only defines the launch-critical routing contract and does not delete anything.
"""
from __future__ import annotations

SOURCE_LANGUAGES = {
    "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW",
}

TARGET_LANGUAGES = {
    "Bangla": "bn",
    "English": "en",
    "Hindi": "hi",
}

TARGET_LABELS = tuple(TARGET_LANGUAGES)


def validate_target_language(language: str) -> str:
    """Return the canonical target code or raise ValueError for V1 UI/API routing."""
    try:
        return TARGET_LANGUAGES[language]
    except KeyError as exc:
        raise ValueError(
            f"V1 supports Chinese drama dubbing to Bangla, English, or Hindi; got {language!r}."
        ) from exc


def is_chinese_source(language: str) -> bool:
    return language in SOURCE_LANGUAGES or language in SOURCE_LANGUAGES.values()

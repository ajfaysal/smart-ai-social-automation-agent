"""Deterministic character-to-voice routing for V1 multilingual dubbing."""
from __future__ import annotations

VOICE_POOLS = {
    "English": ("nova", "onyx", "shimmer", "echo", "fable", "alloy"),
    "Hindi": ("nova", "onyx", "shimmer", "echo", "fable", "alloy"),
}

def voice_for_character(target_language: str, character_id: str, assigned_index: int, requested_voice: str = "auto") -> str:
    """Return one stable provider voice for a character within a dubbing run.

    OpenAI's generic TTS voices are used for English/Hindi V1. Character IDs are
    the stable key; reference-audio cloning is handled by target-specific engines
    when available and is never implied by this generic route.
    """
    if requested_voice != "auto":
        return requested_voice
    pool = VOICE_POOLS.get(target_language, VOICE_POOLS["English"])
    # The assigned index is created once per character, so repeated segments reuse it.
    return pool[assigned_index % len(pool)]

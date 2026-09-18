"""Deterministic acting direction for character TTS and audit manifests."""
from __future__ import annotations

EMOTION_DIRECTIVES = {
 "neutral":"restrained, natural conversational delivery with steady intensity",
 "happy":"warm, bright delivery with a light smile and lifted energy",
 "laughing":"genuine amused delivery with audible laughter, without adding words",
 "sad":"soft, slowed emotional delivery with restrained breathiness",
 "crying":"fragile, tearful delivery with audible emotional strain, without sobbing over words",
 "angry":"firm, tense delivery with controlled force and sharper emphasis",
 "scared":"uneasy, breath-controlled delivery with cautious urgency",
 "surprised":"briefly heightened energy and pitch, then natural conversational recovery",
 "romantic":"warm, intimate, gentle delivery with close conversational energy",
 "whispering":"quiet intimate delivery with clear articulation; never lose intelligibility",
 "shouting":"projected, forceful delivery with strong emphasis while preserving every word",
 "apologetic":"soft, sincere delivery with remorse and lowered intensity",
}

def normalize_emotion(value: str | None) -> str:
    emotion=(value or "neutral").strip().lower()
    return emotion if emotion in EMOTION_DIRECTIVES else "neutral"

def acting_directive(emotion: str | None, profile: str | None = None) -> str:
    normalized=normalize_emotion(emotion)
    profile_hint=(profile or "").strip()
    suffix=f" Character profile: {profile_hint}." if profile_hint else ""
    return EMOTION_DIRECTIVES[normalized] + suffix

"""Audio-layer policy for Chinese drama dubbing.

V1 replaces the original dialogue and original music while retaining the drama
video itself. Conventional two-stem Demucs does not provide a reliable SFX stem,
so V1 does not claim that original SFX are preserved when the full original audio
bed is removed.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioPolicy:
    remove_original_dialogue: bool = True
    remove_original_music: bool = True
    preserve_original_sfx: bool = False

    @property
    def background_separation_required(self) -> bool:
        return self.remove_original_dialogue or self.remove_original_music


V1_AUDIO_POLICY = AudioPolicy()


def describe_policy() -> dict[str, bool]:
    return {
        "remove_original_dialogue": V1_AUDIO_POLICY.remove_original_dialogue,
        "remove_original_music": V1_AUDIO_POLICY.remove_original_music,
        "preserve_original_sfx": V1_AUDIO_POLICY.preserve_original_sfx,
    }


def validate_policy(policy: AudioPolicy) -> None:
    if not policy.remove_original_dialogue:
        raise ValueError("V1 must replace original Chinese dialogue.")
    if not policy.remove_original_music:
        raise ValueError("V1 must remove original music.")

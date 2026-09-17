"""Provider-agnostic voice engine registry for high-character-count dubbing.

The registry is intentionally command-adapter based: model runtimes stay outside
this repository while the dubbing pipeline can route each character to a stable
open-source engine/reference voice. Supported adapter names include:
- cosyvoice
- fish-speech
- gpt-sovits
- openvoice
- edge-neural (fallback)

Each engine receives a command template through an environment variable. This
keeps model weights, checkpoints, reference samples, and credentials out of git.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VoiceEngine:
    name: str
    command_env: str
    supports_cross_lingual: bool
    supports_reference_voice: bool


VOICE_ENGINES = {
    "cosyvoice": VoiceEngine("cosyvoice", "COSYVOICE_TTS_COMMAND", True, True),
    "fish-speech": VoiceEngine("fish-speech", "FISH_SPEECH_TTS_COMMAND", True, True),
    "gpt-sovits": VoiceEngine("gpt-sovits", "GPT_SOVITS_TTS_COMMAND", True, True),
    "openvoice": VoiceEngine("openvoice", "OPENVOICE_TTS_COMMAND", True, True),
    "edge-neural": VoiceEngine("edge-neural", "", True, False),
}


def available_engines() -> list[str]:
    """Return configured engine names in deterministic priority order."""
    return [
        name for name, spec in VOICE_ENGINES.items()
        if name == "edge-neural" or os.getenv(spec.command_env)
    ]


def _reference_exists(reference_dir: Path | None, character_id: str) -> Path | None:
    if not reference_dir:
        return None
    for suffix in (".wav", ".flac", ".mp3"):
        candidate = reference_dir / f"{character_id}{suffix}"
        if candidate.exists():
            return candidate
    return None


def choose_engine(character_id: str, preferred: str | None = None, reference_dir: Path | None = None) -> tuple[str, Path | None]:
    """Choose a configured engine while keeping a stable engine per character."""
    configured = [x for x in available_engines() if x != "edge-neural"]
    if preferred in configured:
        return preferred, _reference_exists(reference_dir, character_id)
    if configured:
        # Stable per-character sharding avoids putting every character on one model.
        index = sum(ord(c) for c in character_id) % len(configured)
        engine = configured[index]
        return engine, _reference_exists(reference_dir, character_id)
    return "edge-neural", None


def run_command_engine(engine: str, text: str, output: Path, reference: Path | None, character_id: str) -> None:
    """Run an external open-source TTS engine through a strict command template."""
    spec = VOICE_ENGINES[engine]
    command = os.getenv(spec.command_env, "")
    if not command:
        raise RuntimeError(f"{engine} is not configured")
    if spec.supports_reference_voice and reference is None:
        raise RuntimeError(f"{engine} requires a reference voice for {character_id}")
    rendered = command.format(
        text=text,
        output=str(output),
        reference=str(reference or ""),
        character=character_id,
    )
    subprocess.run(shlex.split(rendered), check=True, capture_output=True, text=True)
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(f"{engine} did not produce a valid output artifact")

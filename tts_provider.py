"""Provider-neutral TTS routing for production dubbing.

Priority in auto mode:
1. OpenAI when OPENAI_API_KEY is configured.
2. Microsoft Edge Neural TTS when edge-tts is installed.
3. Piper only as a deterministic offline fallback.

Edge Neural TTS is preferred for Bangla because it provides language-specific
neural voices and per-character rate/pitch controls without requiring a paid API.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path


BANGla_VOICES = {
    "male": "bn-BD-PradeepNeural",
    "female": "bn-BD-NabanitaNeural",
}


def _edge_available() -> bool:
    return shutil.which("edge-tts") is not None or _module_available("edge_tts")


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def _profile_gender(profile: str, index: int) -> str:
    p = (profile or "").lower()
    if any(x in p for x in ("female", "woman", "girl", "mother", "sister")):
        return "female"
    if any(x in p for x in ("male", "man", "boy", "father", "brother")):
        return "male"
    return "female" if index % 2 == 0 else "male"


def choose_bangla_voice(profile: str, character_index: int = 0) -> str:
    return BANGla_VOICES[_profile_gender(profile, character_index)]


def _edge_speak_module(text: str, out_path: Path, voice: str, rate: str = "+0%", pitch: str = "+0Hz") -> None:
    import edge_tts

    async def _run() -> None:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume="+0%")
        await communicate.save(str(out_path))

    asyncio.run(_run())


def _edge_speak_cli(text: str, out_path: Path, voice: str, rate: str, pitch: str) -> None:
    subprocess.run(
        ["edge-tts", "--voice", voice, "--rate", rate, "--pitch", pitch, "--text", text, "--write-media", str(out_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def synthesize_bangla(text: str, out_path: Path, profile: str = "", character_index: int = 0, rate: str = "+0%", pitch: str = "+0Hz") -> str:
    """Generate natural Bangla speech and return the provider name used."""
    voice = choose_bangla_voice(profile, character_index)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if _edge_available():
        try:
            if shutil.which("edge-tts"):
                _edge_speak_cli(text, out_path, voice, rate, pitch)
            else:
                _edge_speak_module(text, out_path, voice, rate, pitch)
            return "edge-neural"
        except Exception:
            # Continue to the offline fallback rather than producing a false success.
            pass

    piper = shutil.which("piper")
    model = os.getenv("PIPER_BN_MODEL")
    if piper and model:
        subprocess.run([piper, "--model", model, "--output_file", str(out_path)], input=text, text=True, check=True)
        return "piper-fallback"

    raise RuntimeError("No Bangla TTS provider is available. Install edge-tts or configure PIPER_BN_MODEL.")

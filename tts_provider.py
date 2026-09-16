"""Provider-neutral TTS routing for production dubbing.

Bangla uses Microsoft Edge Neural TTS as the free neural baseline. The router
exposes multiple character profiles: four native Bengali neural voices plus
controlled rate/pitch variants. This lets a drama with many characters keep a
stable identity per character instead of alternating one male and one female
voice.

For truly independent ten-character timbres, the architecture also leaves room
for a reference-audio voice-cloning provider such as IndicF5; no cloned voice
or model weights are bundled in the repository.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path


# Current Microsoft neural Bengali inventory: two Bangladesh voices and two
# India Bengali voices. All are native Bengali neural voices.
BANGLA_BASE_VOICES = {
    "bd_female": "bn-BD-NabanitaNeural",
    "bd_male": "bn-BD-PradeepNeural",
    "in_female": "bn-IN-TanishaaNeural",
    "in_male": "bn-IN-BashkarNeural",
}

# Ten stable character profiles. These are intentionally distinct in base voice
# and delivery style; variants are kept conservative so pitch/rate never become
# cartoonish or robotic.
BANGLA_CHARACTER_PROFILES = {
    "bn_c01_f_young": ("bd_female", "+2%", "+1Hz"),
    "bn_c02_m_young": ("bd_male", "+2%", "+0Hz"),
    "bn_c03_f_adult": ("in_female", "-2%", "-1Hz"),
    "bn_c04_m_adult": ("in_male", "-2%", "-1Hz"),
    "bn_c05_f_mature": ("bd_female", "-7%", "-3Hz"),
    "bn_c06_m_mature": ("bd_male", "-7%", "-3Hz"),
    "bn_c07_f_soft": ("in_female", "-4%", "+2Hz"),
    "bn_c08_m_deep": ("in_male", "-5%", "-4Hz"),
    "bn_c09_f_energetic": ("bd_female", "+5%", "+2Hz"),
    "bn_c10_m_energetic": ("bd_male", "+5%", "+1Hz"),
}

# Backward-compatible aliases used by the existing Bangla pipeline.
BANGla_VOICES = {
    "male": BANGLA_BASE_VOICES["bd_male"],
    "female": BANGLA_BASE_VOICES["bd_female"],
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
    """Return a stable neural voice for a character profile."""
    if profile in BANGLA_CHARACTER_PROFILES:
        base, _, _ = BANGLA_CHARACTER_PROFILES[profile]
        return BANGLA_BASE_VOICES[base]
    if profile in BANGLA_BASE_VOICES:
        return BANGLA_BASE_VOICES[profile]
    return BANGla_VOICES[_profile_gender(profile, character_index)]


def bangla_profile_settings(profile: str, character_index: int = 0) -> tuple[str, str, str]:
    """Return (voice, rate, pitch) for a stable Bangla character identity."""
    if profile in BANGLA_CHARACTER_PROFILES:
        base, rate, pitch = BANGLA_CHARACTER_PROFILES[profile]
        return BANGLA_BASE_VOICES[base], rate, pitch
    gender = _profile_gender(profile, character_index)
    voice = BANGla_VOICES[gender]
    return voice, "+0%", "+0Hz"


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


def synthesize_bangla(
    text: str,
    out_path: Path,
    profile: str = "",
    character_index: int = 0,
    rate: str | None = None,
    pitch: str | None = None,
) -> str:
    """Generate natural Bangla speech and return the provider name used."""
    voice, profile_rate, profile_pitch = bangla_profile_settings(profile, character_index)
    rate = profile_rate if rate is None else rate
    pitch = profile_pitch if pitch is None else pitch
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if _edge_available():
        try:
            if shutil.which("edge-tts"):
                _edge_speak_cli(text, out_path, voice, rate, pitch)
            else:
                _edge_speak_module(text, out_path, voice, rate, pitch)
            return "edge-neural-multicharacter"
        except Exception:
            # Continue to the offline fallback rather than producing a false success.
            pass

    piper = shutil.which("piper")
    model = os.getenv("PIPER_BN_MODEL")
    if piper and model:
        subprocess.run([piper, "--model", model, "--output_file", str(out_path)], input=text, text=True, check=True)
        return "piper-fallback"

    raise RuntimeError("No Bangla TTS provider is available. Install edge-tts or configure PIPER_BN_MODEL.")

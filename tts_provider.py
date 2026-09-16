"""Production Bangla multi-character TTS routing."""
from __future__ import annotations
import asyncio, os, shutil, subprocess
from pathlib import Path

BANGLA_BASE_VOICES = {
    "bd_female": "bn-BD-NabanitaNeural", "bd_male": "bn-BD-PradeepNeural",
    "in_female": "bn-IN-TanishaaNeural", "in_male": "bn-IN-BashkarNeural",
}

# Stable identities: four native Bengali neural bases plus conservative delivery variants.
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
BANGla_VOICES = {"male": BANGLA_BASE_VOICES["bd_male"], "female": BANGLA_BASE_VOICES["bd_female"]}

def _module_available(name: str) -> bool:
    try: __import__(name); return True
    except Exception: return False

def _edge_available() -> bool:
    return shutil.which("edge-tts") is not None or _module_available("edge_tts")

def _profile_gender(profile: str, index: int) -> str:
    p=(profile or "").lower()
    if any(x in p for x in ("female","woman","girl","mother","sister")): return "female"
    if any(x in p for x in ("male","man","boy","father","brother")): return "male"
    return "female" if index % 2 == 0 else "male"

def choose_bangla_voice(profile: str, character_index: int=0) -> str:
    if profile in BANGLA_CHARACTER_PROFILES: return BANGLA_BASE_VOICES[BANGLA_CHARACTER_PROFILES[profile][0]]
    if profile in BANGLA_BASE_VOICES: return BANGLA_BASE_VOICES[profile]
    return BANGla_VOICES[_profile_gender(profile, character_index)]

def bangla_profile_settings(profile: str, character_index: int=0) -> tuple[str,str,str]:
    if profile in BANGLA_CHARACTER_PROFILES:
        base,rate,pitch=BANGLA_CHARACTER_PROFILES[profile]; return BANGLA_BASE_VOICES[base],rate,pitch
    gender=_profile_gender(profile,character_index); return BANGla_VOICES[gender],"+0%","+0Hz"

def _edge_speak_module(text: str,out_path: Path,voice: str,rate: str,pitch: str) -> None:
    import edge_tts
    async def _run(): await edge_tts.Communicate(text,voice,rate=rate,pitch=pitch,volume="+0%").save(str(out_path))
    asyncio.run(_run())

def _edge_speak_cli(text: str,out_path: Path,voice: str,rate: str,pitch: str) -> None:
    subprocess.run(["edge-tts","--voice",voice,"--rate",rate,"--pitch",pitch,"--text",text,"--write-media",str(out_path)],check=True,capture_output=True,text=True)

def _reference_voice_available() -> bool: return bool(os.getenv("BANGLA_REFERENCE_TTS_COMMAND"))

def _reference_speak(text: str,out_path: Path,character_id: str) -> None:
    command=os.getenv("BANGLA_REFERENCE_TTS_COMMAND",""); reference_dir=Path(os.getenv("BANGLA_REFERENCE_VOICE_DIR","")); reference=reference_dir/f"{character_id}.wav"
    if not command: raise RuntimeError("Reference Bangla TTS command is not configured.")
    if not reference.exists(): raise RuntimeError(f"Missing reference voice for {character_id}: {reference}")
    subprocess.run(command.format(text=text,output=str(out_path),reference=str(reference),character=character_id),shell=True,check=True)

def synthesize_bangla(text: str,out_path: Path,profile: str="",character_index: int=0,rate: str|None=None,pitch: str|None=None,character_id: str|None=None) -> str:
    """Prefer configured reference voices; otherwise use Edge Neural; Piper is last-resort fallback."""
    out_path.parent.mkdir(parents=True,exist_ok=True); character_id=character_id or profile or f"character_{character_index+1:02d}"
    if _reference_voice_available():
        try: _reference_speak(text,out_path,character_id); return "reference-audio-bangla"
        except Exception: pass
    voice,pr,pp=bangla_profile_settings(profile,character_index); rate=pr if rate is None else rate; pitch=pp if pitch is None else pitch
    if _edge_available():
        try:
            if shutil.which("edge-tts"): _edge_speak_cli(text,out_path,voice,rate,pitch)
            else: _edge_speak_module(text,out_path,voice,rate,pitch)
            return "edge-neural-multicharacter"
        except Exception: pass
    piper=shutil.which("piper"); model=os.getenv("PIPER_BN_MODEL")
    if piper and model:
        subprocess.run([piper,"--model",model,"--output_file",str(out_path)],input=text,text=True,check=True); return "piper-fallback"
    raise RuntimeError("No Bangla TTS provider is available.")

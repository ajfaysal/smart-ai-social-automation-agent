"""Build a Kaggle GPU notebook for the real end-to-end dubbing smoke run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_notebook(video_url: str, repo: str, ref: str, language: str = "Bangla") -> dict:
    source = f'''import json, os, shutil, subprocess
from pathlib import Path

REPO = Path("/kaggle/working/repo")
INPUT = REPO / "validation-input" / "source.mp4"
CLEAN_VIDEO = REPO / "validation-input" / "cleaned-video.mp4"
CLEAN_REPORT = REPO / "validation-artifacts" / "text-cleanup.json"
ARTIFACTS = Path("/kaggle/working/final-artifacts")
ARTIFACTS.mkdir(parents=True, exist_ok=True)

try:
    from kaggle_secrets import UserSecretsClient
    secrets = UserSecretsClient()
    def secret(name, required=False):
        try:
            value = secrets.get_secret(name)
        except Exception:
            value = ""
        if required and not value:
            raise RuntimeError(f"Missing Kaggle Secret: {{name}}")
        return value
except Exception:
    def secret(name, required=False):
        value = os.getenv(name, "")
        if required and not value:
            raise RuntimeError(f"Missing runtime secret: {{name}}")
        return value

os.environ["OPENAI_API_KEY"] = secret("OPENAI_API_KEY", required=True)
os.environ["LIPSYNC_PROVIDER"] = "wav2lip"
os.environ["FACE_DETECTOR"] = "opencv-haar"
os.environ["MOUTH_LANDMARK_PROVIDER"] = "mediapipe"

subprocess.run(["git", "clone", "--depth", "1", "--branch", {ref!r}, "https://github.com/{repo}.git", str(REPO)], check=True)
subprocess.run(["pip", "install", "-r", "requirements.txt", "-r", "requirements-cloud-runner.txt"], cwd=REPO, check=True)
if {language!r} == "Bangla":
    subprocess.run(["pip", "install", "-q", "edge-tts>=7.0,<8"], check=True)
subprocess.run(["python", "run_cloud_smoke.py", {video_url!r}, "--output", str(INPUT), "--report", str(REPO / "validation-artifacts" / "cloud-input.json")], cwd=REPO, check=True)

# Clean burned-in Chinese text before dubbing. The cleaner emits video-only;
# muxing the source audio back here is temporary so dub_video can extract it.
cleanup_code = "from pathlib import Path; from scene_analysis import detect_shots; from video_text_cleaner import clean_video; p=Path('validation-input/source.mp4'); cuts=[x['time'] for x in detect_shots(p)]; clean_video(p, Path('validation-input/cleaned-video.mp4'), Path('validation-artifacts/text-cleanup.json'), languages=['ch_sim','en'], scene_cuts=cuts)"
subprocess.run(["python", "-c", cleanup_code], cwd=REPO, check=True)
MUXED = REPO / "validation-input" / "cleaned-with-audio.mp4"
subprocess.run(["ffmpeg", "-y", "-i", str(CLEAN_VIDEO), "-i", str(INPUT), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(MUXED)], check=True)

wav_repo = Path("/kaggle/working/Wav2Lip")
subprocess.run(["git", "clone", "--depth", "1", "https://github.com/Rudrabha/Wav2Lip.git", str(wav_repo)], check=True)
subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=wav_repo, check=True)
ckpt_url = secret("WAV2LIP_CHECKPOINT_URL", required=True)
s3fd_url = secret("WAV2LIP_S3FD_URL", required=True)
subprocess.run(["mkdir", "-p", str(wav_repo / "checkpoints"), str(wav_repo / "face_detection" / "detection" / "sfd")], check=True)
subprocess.run(["wget", "-q", "-O", str(wav_repo / "checkpoints" / "wav2lip.pth"), ckpt_url], check=True)
subprocess.run(["wget", "-q", "-O", str(wav_repo / "face_detection" / "detection" / "sfd" / "s3fd.pth"), s3fd_url], check=True)

wrapper = Path("/kaggle/working/wav2lip")
wrapper.write_text("""#!/bin/sh
set -eu
VIDEO=""; AUDIO=""; CKPT=""; OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --video) VIDEO="$2"; shift 2;;
    --audio) AUDIO="$2"; shift 2;;
    --checkpoint) CKPT="$2"; shift 2;;
    --outfile) OUT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
exec python /kaggle/working/Wav2Lip/inference.py --checkpoint_path "$CKPT" --face "$VIDEO" --audio "$AUDIO" --outfile "$OUT"
""", encoding="utf-8")
wrapper.chmod(0o755)
os.environ["WAV2LIP_COMMAND"] = str(wrapper)
os.environ["WAV2LIP_MODEL_PATH"] = str(wav_repo / "checkpoints" / "wav2lip.pth")

import drama_dubbing
from tts_provider import synthesize_bangla

BANGLA_CHARACTER_VOICE_POOL = [
    "bn_c01_f_young", "bn_c02_m_young", "bn_c03_f_adult", "bn_c04_m_adult",
    "bn_c05_f_mature", "bn_c06_m_mature", "bn_c07_f_soft", "bn_c08_m_deep",
    "bn_c09_f_energetic", "bn_c10_m_energetic",
]

def _profile_from_hint(hint, character_index):
    hint = str(hint or "").strip().lower()
    exact = {p.lower(): p for p in BANGLA_CHARACTER_VOICE_POOL}
    if hint in exact:
        return exact[hint]
    female = any(x in hint for x in ("female", "woman", "girl", "mother", "sister"))
    male = any(x in hint for x in ("male", "man", "boy", "father", "brother"))
    if female:
        return BANGLA_CHARACTER_VOICE_POOL[(character_index * 2) % 10]
    if male:
        return BANGLA_CHARACTER_VOICE_POOL[((character_index * 2) + 1) % 10]
    return BANGLA_CHARACTER_VOICE_POOL[character_index % 10]

_original_director_plan = drama_dubbing.director_plan

def bangla_director_plan(segments):
    plan = _original_director_plan(segments)
    character_slots = {}
    for i, info in plan.items():
        char = str(info.get("character") or f"C{i+1}")
        if char not in character_slots:
            character_slots[char] = len(character_slots)
        info["profile"] = _profile_from_hint(info.get("profile"), character_slots[char])
    return plan

def natural_bangla_tts(text, out_path, voice, emotion):
    synthesize_bangla(text, Path(out_path), profile=voice)

def quality_master_mix(background, dubbed, music, total, work):
    out = Path(work) / "master.wav"
    subprocess.run(["ffmpeg", "-y", "-i", str(dubbed), "-filter_complex", "[0:a]highpass=f=75,lowpass=f=15000,acompressor=threshold=0.25:ratio=2:attack=20:release=180:makeup=1.0,alimiter=limit=0.94,loudnorm=I=-16:TP=-1.5:LRA=8,alimiter=limit=0.95[a]", "-map", "[a]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", "-t", f"{total:.3f}", str(out)], check=True)
    return out

if {language!r} == "Bangla":
    drama_dubbing.VOICE_POOL = BANGLA_CHARACTER_VOICE_POOL
    drama_dubbing.director_plan = bangla_director_plan
    drama_dubbing.make_tts = natural_bangla_tts
    drama_dubbing.master_mix = quality_master_mix

output, mood, lip = drama_dubbing.dub_video(MUXED, {language!r}, requested_voice="auto", preserve_background=False, add_mood_music=False, lip_sync=True)
manifest = output.with_suffix(".json")
subtitle = output.with_suffix(".srt")
for path in (output, manifest, subtitle):
    if path.exists(): shutil.copy2(path, ARTIFACTS / path.name)
if CLEAN_REPORT.exists(): shutil.copy2(CLEAN_REPORT, ARTIFACTS / CLEAN_REPORT.name)

report = {
    "status": "certified" if output.exists() and manifest.exists() and lip and lip.get("applied") else "failed_closed",
    "output": str(ARTIFACTS / output.name),
    "manifest": str(ARTIFACTS / manifest.name),
    "subtitle": str(ARTIFACTS / subtitle.name),
    "text_cleanup_report": str(ARTIFACTS / CLEAN_REPORT.name),
    "mood": mood,
    "lip_sync": lip,
    "voice_engine": "edge-neural-bangla-multicharacter" if {language!r} == "Bangla" else "canonical-openai",
    "character_voice_profiles": BANGLA_CHARACTER_VOICE_POOL if {language!r} == "Bangla" else [],
    "audio_mix": "replacement-dialogue-only-no-original-music",
    "original_dialogue_removed": True,
    "original_music_removed": True,
    "source_text_cleanup": "ocr-guided-easyocr-opencv-inpaint",
}
(ARTIFACTS / "cloud-provider-certification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
'''
    return {"cells": [{"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(True)}], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "nbformat": 4, "nbformat_minor": 5}}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--video-url", required=True)
    p.add_argument("--repo", default="ajfaysal/smart-ai-social-automation-agent")
    p.add_argument("--ref", default="main")
    p.add_argument("--language", default="Bangla", choices=["Bangla", "English", "Hindi"])
    p.add_argument("--output", default="kaggle_full_pipeline.ipynb")
    args = p.parse_args()
    notebook = build_notebook(args.video_url, args.repo, args.ref, args.language)
    Path(args.output).write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

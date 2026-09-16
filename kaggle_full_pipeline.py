"""Build a Kaggle GPU notebook for the real end-to-end dubbing smoke run.

Secrets and model weights are runtime-only. The generated notebook reads Kaggle
Secrets for OpenAI and Wav2Lip assets, then executes the repository's canonical
`dub_video` pipeline against the public cloud input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_notebook(video_url: str, repo: str, ref: str, language: str = "Chinese (Simplified)") -> dict:
    source = f'''import json, os, shutil, subprocess
from pathlib import Path

REPO = Path("/kaggle/working/repo")
INPUT = REPO / "validation-input" / "source.mp4"
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
subprocess.run(["python", "run_cloud_smoke.py", {video_url!r}, "--output", str(INPUT), "--report", str(REPO / "validation-artifacts" / "cloud-input.json")], cwd=REPO, check=True)

wav_repo = Path("/kaggle/working/Wav2Lip")
subprocess.run(["git", "clone", "--depth", "1", "https://github.com/Rudrabha/Wav2Lip.git", str(wav_repo)], check=True)
subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=wav_repo, check=True)
ckpt_url = secret("WAV2LIP_CHECKPOINT_URL", required=True)
s3fd_url = secret("WAV2LIP_S3FD_URL", required=True)
subprocess.run(["mkdir", "-p", str(wav_repo / "checkpoints"), str(wav_repo / "face_detection" / "detection" / "sfd")], check=True)
subprocess.run(["wget", "-q", "-O", str(wav_repo / "checkpoints" / "wav2lip.pth"), ckpt_url], check=True)
subprocess.run(["wget", "-q", "-O", str(wav_repo / "face_detection" / "detection" / "sfd" / "s3fd.pth"), s3fd_url], check=True)

wrapper = Path("/kaggle/working/wav2lip")
wrapper.write_text("""#!/bin/sh\nset -eu\nVIDEO=\"\"; AUDIO=\"\"; CKPT=\"\"; OUT=\"\"\nwhile [ $# -gt 0 ]; do\n  case \"$1\" in\n    --video) VIDEO=\"$2\"; shift 2;;\n    --audio) AUDIO=\"$2\"; shift 2;;\n    --checkpoint) CKPT=\"$2\"; shift 2;;\n    --outfile) OUT=\"$2\"; shift 2;;\n    *) echo \"unknown arg: $1\" >&2; exit 2;;\n  esac\ndone\nexec python /kaggle/working/Wav2Lip/inference.py --checkpoint_path \"$CKPT\" --face \"$VIDEO\" --audio \"$AUDIO\" --outfile \"$OUT\"\n""", encoding="utf-8")
wrapper.chmod(0o755)
os.environ["WAV2LIP_COMMAND"] = str(wrapper)
os.environ["WAV2LIP_MODEL_PATH"] = str(wav_repo / "checkpoints" / "wav2lip.pth")

# Bangla uses Microsoft Edge Neural TTS instead of the robotic Piper fallback.
import drama_dubbing
from tts_provider import synthesize_bangla

def natural_bangla_tts(text, out_path, voice, emotion):
    profile = "female" if voice in {{"nova", "shimmer", "fable"}} else "male"
    synthesize_bangla(text, Path(out_path), profile=profile)

def quality_master_mix(background, dubbed, music, total, work):
    """Speech-first mix with real sidechain ducking instead of static bed volume."""
    out = Path(work) / "master.wav"
    inputs = ["-i", str(dubbed)]
    filters = ["[0:a]highpass=f=75,lowpass=f=15000,acompressor=threshold=0.25:ratio=2:attack=20:release=180:makeup=1.0,alimiter=limit=0.94[voice]"]
    idx = 1
    bed_layers = []
    if background:
        inputs += ["-i", str(background)]
        filters.append(f"[{idx}:a]highpass=f=45,lowpass=f=16000,volume=0.80[bg]")
        bed_layers.append("[bg]")
        idx += 1
    if music:
        inputs += ["-i", str(music)]
        filters.append(f"[{idx}:a]volume=0.035[music]")
        bed_layers.append("[music]")
    if bed_layers:
        filters.append("".join(bed_layers) + f"amix=inputs={len(bed_layers)}:duration=longest:dropout_transition=0:normalize=0[bed]")
        filters.append("[bed][voice]sidechaincompress=threshold=0.025:ratio=8:attack=18:release=320:makeup=1[ducked]")
        filters.append("[ducked][voice]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=8,alimiter=limit=0.95[a]")
    else:
        filters.append("[voice]loudnorm=I=-16:TP=-1.5:LRA=8,alimiter=limit=0.95[a]")
    subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[a]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", "-t", f"{total:.3f}", str(out)], check=True)
    return out

if {language!r} == "Bangla":
    drama_dubbing.make_tts = natural_bangla_tts
    drama_dubbing.master_mix = quality_master_mix

output, mood, lip = drama_dubbing.dub_video(
    INPUT,
    {language!r},
    requested_voice="auto",
    preserve_background=True,
    add_mood_music=True,
    lip_sync=True,
)

manifest = output.with_suffix(".json")
subtitle = output.with_suffix(".srt")
for path in (output, manifest, subtitle):
    if path.exists():
        shutil.copy2(path, ARTIFACTS / path.name)

report = {{
    "status": "certified" if output.exists() and manifest.exists() and lip and lip.get("applied") else "failed_closed",
    "output": str(ARTIFACTS / output.name),
    "manifest": str(ARTIFACTS / manifest.name),
    "subtitle": str(ARTIFACTS / subtitle.name),
    "mood": mood,
    "lip_sync": lip,
    "voice_engine": "edge-neural-bangla" if {language!r} == "Bangla" else "canonical-openai",
    "audio_mix": "sidechain-ducked-speech-first",
}}
(ARTIFACTS / "cloud-provider-certification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
'''
    return {
        "cells": [{"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(True)}],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.x"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--video-url", required=True)
    p.add_argument("--repo", default="ajfaysal/smart-ai-social-automation-agent")
    p.add_argument("--ref", default="main")
    p.add_argument("--language", default="Chinese (Simplified)")
    p.add_argument("--output", default="kaggle_full_pipeline.ipynb")
    args = p.parse_args()
    notebook = build_notebook(args.video_url, args.repo, args.ref, args.language)
    Path(args.output).write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

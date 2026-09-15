"""Build a Kaggle GPU notebook for the real end-to-end dubbing smoke run.

Secrets and model weights are runtime-only. The generated notebook reads Kaggle
Secrets for OpenAI and Wav2Lip assets, then executes the repository's canonical
`dub_video` pipeline against the public cloud input.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path


def build_notebook(video_url: str, repo: str, ref: str, language: str = "Chinese (Simplified)") -> dict:
    source = f'''import json, os, shutil, subprocess
from pathlib import Path

REPO = Path("/kaggle/working/repo")
INPUT = REPO / "validation-input" / "source.mp4"
OUT = REPO / "dubbed_output"
ARTIFACTS = Path("/kaggle/working/final-artifacts")
ARTIFACTS.mkdir(parents=True, exist_ok=True)

# Runtime-only secrets. Nothing below writes credentials into Git.
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

# Fetch the public Drive fixture and validate video+audio+duration first.
subprocess.run(["python", "run_cloud_smoke.py", {video_url!r}, "--output", str(INPUT), "--report", str(REPO / "validation-artifacts" / "cloud-input.json")], cwd=REPO, check=True)

# Install Wav2Lip only inside the ephemeral Kaggle runtime. The checkpoint and
# S3FD detector are supplied through Kaggle Secrets as URLs, never committed.
wav_repo = Path("/kaggle/working/Wav2Lip")
subprocess.run(["git", "clone", "--depth", "1", "https://github.com/Rudrabha/Wav2Lip.git", str(wav_repo)], check=True)
subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=wav_repo, check=True)
ckpt_url = secret("WAV2LIP_CHECKPOINT_URL", required=True)
s3fd_url = secret("WAV2LIP_S3FD_URL", required=True)
subprocess.run(["mkdir", "-p", str(wav_repo / "checkpoints"), str(wav_repo / "face_detection" / "detection" / "sfd")], check=True)
subprocess.run(["wget", "-q", "-O", str(wav_repo / "checkpoints" / "wav2lip.pth"), ckpt_url], check=True)
subprocess.run(["wget", "-q", "-O", str(wav_repo / "face_detection" / "detection" / "sfd" / "s3fd.pth"), s3fd_url], check=True)

# Adapt the canonical provider CLI contract to the upstream Wav2Lip inference CLI.
wrapper = Path("/kaggle/working/wav2lip")
wrapper.write_text("""#!/bin/sh\nset -eu\nVIDEO=\"\"; AUDIO=\"\"; CKPT=\"\"; OUT=\"\"\nwhile [ $# -gt 0 ]; do\n  case \"$1\" in\n    --video) VIDEO=\"$2\"; shift 2;;\n    --audio) AUDIO=\"$2\"; shift 2;;\n    --checkpoint) CKPT=\"$2\"; shift 2;;\n    --outfile) OUT=\"$2\"; shift 2;;\n    *) echo \"unknown arg: $1\" >&2; exit 2;;\n  esac\ndone\nexec python /kaggle/working/Wav2Lip/inference.py --checkpoint_path \"$CKPT\" --face \"$VIDEO\" --audio \"$AUDIO\" --outfile \"$OUT\"\n""", encoding="utf-8")
wrapper.chmod(0o755)
os.environ["WAV2LIP_COMMAND"] = str(wrapper)
os.environ["WAV2LIP_MODEL_PATH"] = str(wav_repo / "checkpoints" / "wav2lip.pth")

# Execute the canonical production pipeline: STT -> character/emotion director
# -> Chinese translation/TTS -> exact timing -> Demucs background preservation
# -> mood music/mastering -> shot-aware Wav2Lip -> final QC + manifest.
from drama_dubbing import dub_video
output, mood, lip = dub_video(
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

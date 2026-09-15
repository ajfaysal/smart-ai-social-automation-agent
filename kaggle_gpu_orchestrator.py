"""Launch the real-provider dubbing smoke pipeline on a Kaggle GPU kernel.

Credentials are runtime-only. The generated kernel never contains API secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def _token() -> str:
    token = os.getenv("KAGGLE_API_TOKEN") or os.getenv("KAGGLE_API_KEY")
    if not token:
        raise RuntimeError("Kaggle credential missing: set KAGGLE_API_TOKEN or KAGGLE_API_KEY")
    return token


def build_notebook(video_url: str, repo: str, ref: str, profile: str) -> dict:
    source = f'''import os, subprocess, json
from pathlib import Path

REPO = Path("/kaggle/working/repo")
subprocess.run(["git", "clone", "--depth", "1", "--branch", {ref!r}, "https://github.com/{repo}.git", str(REPO)], check=True)
subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=REPO, check=True)
subprocess.run(["pip", "install", "-r", "requirements-cloud-runner.txt"], cwd=REPO, check=True)
subprocess.run(["python", "run_cloud_smoke.py", {video_url!r}, "--output", "validation-input/source.mp4"], cwd=REPO, check=True)

# The production runner records provider execution only after validated artifacts.
# Demucs is always run first because its output becomes the background source.
subprocess.run(["python", "real_provider_runner.py", "demucs", "--audio", "validation-input/source.mp4", "--work", "provider-validation-work"], cwd=REPO, check=True)

if {profile!r} == "full":
    image = os.getenv("LIPSYNC_SMOKE_IMAGE", "")
    if image:
        subprocess.run(["python", "real_provider_runner.py", "mediapipe", "--image", image, "--work", "provider-validation-work"], cwd=REPO, check=True)
    else:
        print("MediaPipe: awaiting operator-provided frame/image; no false success recorded")

    video = os.getenv("WAV2LIP_INPUT_VIDEO", "")
    audio = os.getenv("WAV2LIP_INPUT_AUDIO", "")
    output = os.getenv("WAV2LIP_OUTPUT", "/kaggle/working/wav2lip-output.mp4")
    if video and audio:
        subprocess.run(["python", "real_provider_runner.py", "wav2lip", "--video", video, "--audio", audio, "--output", output, "--work", "provider-validation-work"], cwd=REPO, check=True)
    else:
        print("Wav2Lip: awaiting operator-provided runtime inputs/checkpoint; no false success recorded")

print(json.dumps({"profile": {profile!r}, "input": "validation-input/source.mp4", "provider_work": "provider-validation-work"}, indent=2))
'''
    return {
        "cells": [{"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(True)}],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.x"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Push a Kaggle GPU provider smoke kernel")
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--repo", default="ajfaysal/smart-ai-social-automation-agent")
    parser.add_argument("--ref", default="main")
    parser.add_argument("--profile", choices=("demucs", "full"), default="full")
    parser.add_argument("--kernel-slug", default="drama-dubbing-real-provider-smoke")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    notebook = build_notebook(args.video_url, args.repo, args.ref, args.profile)
    if args.dry_run:
        print(json.dumps(notebook, indent=2))
        return 0

    _token()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "provider_smoke.ipynb").write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
        metadata = {
            "id": f"ajfaysal/{args.kernel_slug}",
            "title": "Drama Dubbing Real Provider Smoke",
            "code_file": "provider_smoke.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": True,
            "enable_gpu": True,
            "enable_internet": True,
        }
        (root / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return subprocess.run(["kaggle", "kernels", "push", "-p", str(root)], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

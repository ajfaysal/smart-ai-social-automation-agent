"""Push the real end-to-end dubbing pipeline to a Kaggle GPU kernel.

Credentials, model URLs, and media remain runtime-only. The generated kernel
reads them from Kaggle Secrets and executes the repository's canonical
``dub_video`` pipeline.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from kaggle_full_pipeline import build_notebook
from real_run_preflight import build_preflight

DEFAULT_VIDEO_URL = "https://drive.google.com/file/d/1brOpsZOsoM2oWijxbYyHKDlDrsQTnO7-/view?usp=drivesdk"


def _token() -> str:
    token = os.getenv("KAGGLE_API_TOKEN") or os.getenv("KAGGLE_API_KEY")
    if not token:
        raise RuntimeError("Kaggle credential missing: set KAGGLE_API_TOKEN or KAGGLE_API_KEY")
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description="Push the full drama dubbing pipeline to a Kaggle GPU kernel")
    parser.add_argument("--video-url", default=DEFAULT_VIDEO_URL)
    parser.add_argument("--repo", default="ajfaysal/smart-ai-social-automation-agent")
    parser.add_argument("--ref", default="main")
    parser.add_argument("--language", default="Bangla", choices=["Bangla", "English", "Hindi"])
    parser.add_argument("--kernel-slug", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dispatch-only", action="store_true", help="Build and submit the Kaggle kernel without requiring provider runtime secrets in GitHub.")
    args = parser.parse_args()

    if args.dispatch_only:
        # Provider secrets belong to Kaggle Secrets and must not be duplicated in GitHub.
        preflight = build_preflight(
            video_url=args.video_url,
            target_language=args.language,
            require_openai=False,
            require_wav2lip=False,
            require_diarization=False,
            require_whisper_xtts=False,
        )
    else:
        preflight = build_preflight(
            video_url=args.video_url,
            target_language=args.language,
            require_openai=not args.dry_run,
            require_wav2lip=not args.dry_run,
            require_diarization=not args.dry_run,
            require_whisper_xtts=not args.dry_run,
        )
    if not preflight.ready:
        print(json.dumps({"ready": False, "missing_secrets": preflight.missing_secrets, "missing_runtime": preflight.missing_runtime}, ensure_ascii=False))
        return 2
    notebook = build_notebook(args.video_url, args.repo, args.ref, args.language)
    if args.dry_run:
        print(json.dumps(notebook, ensure_ascii=False, indent=2))
        return 0

    _token()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "kaggle_full_pipeline.ipynb").write_text(
            json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        metadata = {
            "id": f"ajfaysal/{args.kernel_slug or f'drama-dubbing-chinese-{args.language.lower()}' }",
            "title": f"Chinese Drama → {args.language} Dubbing",
            "code_file": "kaggle_full_pipeline.ipynb",
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

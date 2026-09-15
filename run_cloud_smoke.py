"""Operator-side cloud video smoke runner.

Downloads and validates a public media URL, then records the input evidence.
Provider execution remains explicit so this script never claims a real provider
ran when it did not.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cloud_video_input import download_url, validate_media


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and validate a cloud video fixture")
    parser.add_argument("url")
    parser.add_argument("--output", default="validation-input/source.mp4")
    parser.add_argument("--report", default="validation-artifacts/cloud-input.json")
    args = parser.parse_args()

    output = Path(args.output)
    report = Path(args.report)
    downloaded = download_url(args.url, output)
    media = validate_media(downloaded)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"input": media, "validated": True}, indent=2), encoding="utf-8")
    print(json.dumps(media, indent=2))


if __name__ == "__main__":
    main()

"""Download public cloud-hosted video fixtures for provider smoke tests.

Supports Google Drive share links and ordinary direct HTTP(S) URLs. The
runner never stores credentials or cloud tokens in the repository.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests


def google_drive_file_id(url: str) -> str | None:
    parsed = urlparse(url)
    match = re.search(r"/file/d/([A-Za-z0-9_-]+)", parsed.path)
    if match:
        return match.group(1)
    query_id = parse_qs(parsed.query).get("id", [None])[0]
    return query_id


def download_url(url: str, destination: Path, timeout: int = 60) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_id = google_drive_file_id(url)
    if file_id:
        url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"

    with requests.get(url, stream=True, timeout=timeout, allow_redirects=True) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type.lower():
            raise RuntimeError(
                "download_returned_html: public file endpoint did not return video bytes"
            )
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)

    if not destination.is_file() or destination.stat().st_size < 1024:
        raise RuntimeError("downloaded_video_too_small")
    return destination


def validate_media(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe_unavailable")
    completed = subprocess.run(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"ffprobe_failed:{completed.stderr[-500:]}")
    import json
    data = json.loads(completed.stdout)
    streams = data.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    duration = float(data.get("format", {}).get("duration", 0))
    if not video or not audio or duration < 0.1:
        raise RuntimeError("invalid_video_fixture")
    return {"path": str(path), "size_bytes": path.stat().st_size,
            "duration": duration, "video_streams": len(video),
            "audio_streams": len(audio), "validated": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--output", default="validation-input/source.mp4")
    args = parser.parse_args()
    path = download_url(args.url, Path(args.output))
    print(validate_media(path))


if __name__ == "__main__":
    main()

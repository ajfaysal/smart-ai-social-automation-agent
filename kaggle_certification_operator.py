"""Poll and retrieve outputs from a Kaggle real-certification kernel.

This tool never treats submission as certification. A certification is valid only
when the downloaded certification.json reports certified=true.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


TERMINAL_SUCCESS = ("complete", "completed", "success", "succeeded")
TERMINAL_FAILURE = ("failed", "failure", "error", "errored", "cancelled", "canceled")


def kernel_status(kernel: str) -> str:
    result = subprocess.run(
        ["kaggle", "kernels", "status", kernel],
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(output or f"Kaggle status failed with exit code {result.returncode}")
    return output


def classify_status(raw: str) -> str:
    text = raw.lower()
    if any(token in text for token in TERMINAL_FAILURE):
        return "failed"
    if any(token in text for token in TERMINAL_SUCCESS):
        return "completed"
    if "running" in text or "queued" in text or "pending" in text:
        return "running"
    return "unknown"


def wait_for_completion(kernel: str, timeout_seconds: int, poll_seconds: int) -> tuple[str, str]:
    deadline = time.monotonic() + timeout_seconds
    last = ""
    while True:
        last = kernel_status(kernel)
        state = classify_status(last)
        if state in {"completed", "failed"}:
            return state, last
        if time.monotonic() >= deadline:
            return "timeout", last
        time.sleep(max(1, poll_seconds))


def download_output(kernel: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["kaggle", "kernels", "output", kernel, "-p", str(output_dir), "-o", "-q"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stdout + "\n" + result.stderr).strip())



def validate_downloaded_artifacts(output_dir: Path) -> dict:
    certification_files = list(output_dir.rglob("certification.json"))
    if len(certification_files) != 1:
        raise RuntimeError("Expected exactly one certification.json in Kaggle output")
    data = json.loads(certification_files[0].read_text(encoding="utf-8"))
    if data.get("certified") is not True:
        raise RuntimeError(f"Kaggle run completed without certification: {data.get('reason', 'unknown reason')}")
    report_files = list(output_dir.rglob("cloud-provider-certification.json"))
    if len(report_files) != 1:
        raise RuntimeError("Expected exactly one cloud-provider-certification.json in Kaggle output")
    report = json.loads(report_files[0].read_text(encoding="utf-8"))
    if report.get("status") != "certified":
        raise RuntimeError("Kaggle output report is not certified")
    reported_output = str(report.get("output", "")).strip()
    if not reported_output:
        raise RuntimeError("Kaggle output report does not identify the final video")
    final_name = Path(reported_output).name
    videos = [p for p in output_dir.rglob("*.mp4") if p.name == final_name]
    if len(videos) != 1:
        raise RuntimeError("Expected exactly one MP4 matching the certified final output")
    final_video = videos[0]
    required = {"speaker-identity.json", "speaker-routing.json", "text-cleanup.json"}
    available = {p.name for p in output_dir.rglob("*") if p.is_file()}
    missing = sorted(required - available)
    if missing:
        raise RuntimeError("Certified output is missing evidence artifacts: " + ", ".join(missing))
    manifest = final_video.with_suffix(".json")
    if not manifest.is_file():
        raise RuntimeError("Certified output is missing the final dubbing manifest beside the MP4")
    import hashlib
    digest = hashlib.sha256(final_video.read_bytes()).hexdigest()
    return {"certification": data, "final_video": str(final_video), "final_video_sha256": digest, "manifest": str(manifest), "evidence": sorted(required), "cloud_report": str(report_files[0])}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel")
    parser.add_argument("--timeout", type=int, default=0, help="Seconds to wait; 0 checks status once")
    parser.add_argument("--poll", type=int, default=30)
    parser.add_argument("--output-dir", default="kaggle-certification-output")
    args = parser.parse_args()

    if args.timeout:
        state, raw = wait_for_completion(args.kernel, args.timeout, args.poll)
    else:
        raw = kernel_status(args.kernel)
        state = classify_status(raw)

    print(json.dumps({"kernel": args.kernel, "state": state, "status": raw}, ensure_ascii=False, indent=2))
    if state != "completed":
        return 2

    output_dir = Path(args.output_dir)
    download_output(args.kernel, output_dir)
    evidence = validate_downloaded_artifacts(output_dir)
    print(json.dumps({"certified": True, **evidence}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Shot-level lip-sync orchestration.

This module prepares eligible shot clips, invokes the configured provider, and
reassembles the untouched and processed shots in source order. It never marks
a shot as processed unless the provider reports success.
"""
from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess


def _run(args: list[str]) -> None:
    subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _cut(video: Path, start: float, end: float, out: Path) -> None:
    _run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{max(0.001, end-start):.3f}",
          "-map", "0:v:0", "-map", "0:a:0?", "-c", "copy", "-avoid_negative_ts", "make_zero", str(out)])


def _concat(parts: list[Path], output: Path) -> None:
    listing = output.parent / f"{output.stem}_concat.txt"
    listing.write_text("".join(f"file '{p.as_posix().replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for p in parts), encoding="utf-8")
    try:
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(output)])
    finally:
        listing.unlink(missing_ok=True)


def process_shots(video: Path, dubbed_audio: Path, output: Path, work_dir: Path, shots: list[dict], provider) -> dict:
    """Process only eligible shots; untouched shots remain byte-level source clips."""
    from face_tracking import track_shot

    work_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    records = []
    for shot in shots:
        idx = int(shot.get("index", len(parts)))
        start = float(shot.get("start", 0.0))
        end = float(shot.get("end", start))
        source_part = work_dir / f"shot_{idx:05d}_source.mp4"
        _cut(video, start, end, source_part)
        eligibility = track_shot(video, start, end)
        result = None
        chosen = source_part
        if eligibility.get("eligible") and provider.available():
            audio_part = work_dir / f"shot_{idx:05d}_audio.wav"
            _run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(dubbed_audio), "-t", f"{max(0.001,end-start):.3f}", "-ac", "1", "-ar", "48000", str(audio_part)])
            processed = work_dir / f"shot_{idx:05d}_lipsync.mp4"
            result = provider.apply(source_part, audio_part, processed)
            if result.applied and Path(result.output_path).exists():
                chosen = Path(result.output_path)
        parts.append(chosen)
        records.append({"shot": idx, "start": start, "end": end,
                        "eligible": bool(eligibility.get("eligible")),
                        "provider": getattr(provider, "name", "unknown"),
                        "applied": bool(result and result.applied),
                        "reason": result.reason if result else eligibility.get("reason", "Provider not run."),
                        "output": chosen.name})
    _concat(parts, output)
    manifest = work_dir / "shot_lipsync_manifest.json"
    manifest.write_text(json.dumps({"version":"1.0","mode":"shot-aware","records":records,
                                    "applied_shots":sum(r["applied"] for r in records),
                                    "eligible_shots":sum(r["eligible"] for r in records)}, indent=2), encoding="utf-8")
    return {"output_path": output, "manifest": manifest, "records": records}

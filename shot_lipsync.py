"""Shot-level lip-sync orchestration.

Processes only face-eligible shots with a configured real provider, preserves
untouched shots, and reassembles the visual track. The caller attaches the
single global dubbed-audio timeline after this visual pass.
"""
from __future__ import annotations

from pathlib import Path
import json
import subprocess


def _run(args: list[str]) -> None:
    subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _cut(video: Path, start: float, end: float, out: Path) -> None:
    _run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{max(0.001, end-start):.3f}",
          "-map", "0:v:0", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
          "-pix_fmt", "yuv420p", str(out)])


def _cut_audio(audio: Path, start: float, end: float, out: Path) -> None:
    _run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(audio), "-t", f"{max(0.001,end-start):.3f}",
          "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(out)])


def _concat(parts: list[Path], output: Path) -> None:
    listing = output.parent / f"{output.stem}_concat.txt"
    listing.write_text("".join(f"file '{p.as_posix().replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for p in parts), encoding="utf-8")
    try:
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
              "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
              "-pix_fmt", "yuv420p", str(output)])
    finally:
        listing.unlink(missing_ok=True)


def process_shots(video: Path, dubbed_audio: Path, output: Path, work_dir: Path, shots: list[dict], provider, face_tracks: list[dict] | None = None) -> dict:
    """Process eligible shots and return a video-only reassembled timeline."""
    work_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    records = []
    by_shot = {int(r.get("shot")): r for r in (face_tracks or []) if r.get("shot") is not None}
    for position, shot in enumerate(shots):
        idx = int(shot.get("index", position))
        start = float(shot.get("start", 0.0))
        end = float(shot.get("end", start))
        source_part = work_dir / f"shot_{idx:05d}_source.mp4"
        _cut(video, start, end, source_part)
        eligibility = by_shot.get(idx, {"eligible": False, "reason": "No face-track record for shot."})
        result = None
        chosen = source_part
        status = "fallback"
        if eligibility.get("eligible") and provider.available():
            audio_part = work_dir / f"shot_{idx:05d}_audio.wav"
            _cut_audio(dubbed_audio, start, end, audio_part)
            processed = work_dir / f"shot_{idx:05d}_lipsync.mp4"
            try:
                result = provider.apply(source_part, audio_part, processed)
                if result.applied and Path(result.output_path).exists():
                    chosen = Path(result.output_path)
                    status = "applied"
            except Exception as exc:
                status = "error"
                records.append({"shot": idx, "start": start, "end": end, "eligible": True,
                                "status": status, "provider": getattr(provider, "name", "unknown"),
                                "reason": str(exc)[-1000:], "output": source_part.name})
                parts.append(source_part)
                continue
        parts.append(chosen)
        records.append({"shot": idx, "start": start, "end": end,
                        "eligible": bool(eligibility.get("eligible")), "status": status,
                        "provider": getattr(provider, "name", "unknown"),
                        "reason": result.reason if result else eligibility.get("reason", "Provider not run."),
                        "output": chosen.name})
    if not parts:
        raise ValueError("No shots available for reassembly.")
    _concat(parts, output)
    manifest = work_dir / "shot_lipsync_manifest.json"
    manifest.write_text(json.dumps({"version": "1.1", "mode": "shot-aware",
                                    "video_only_reassembly": True, "records": records,
                                    "applied_shots": sum(r["status"] == "applied" for r in records),
                                    "eligible_shots": sum(r["eligible"] for r in records),
                                    "total_shots": len(records)}, indent=2), encoding="utf-8")
    return {"output_path": output, "manifest": manifest, "records": records}

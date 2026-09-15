"""Shot-level lip-sync orchestration with video-only reassembly."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess

from provider_runtime import snapshot


def _run(args: list[str]) -> None:
    completed = subprocess.run(args, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr[-3000:] or "FFmpeg command failed")


def _cut(video: Path, start: float, end: float, out: Path) -> None:
    _run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{max(0.001, end-start):.3f}",
          "-map", "0:v:0", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
          "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart", str(out)])


def _cut_audio(audio: Path, start: float, end: float, out: Path) -> None:
    _run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(audio), "-t", f"{max(0.001,end-start):.3f}",
          "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(out)])


def _normalize_video(video: Path, output: Path) -> None:
    _run(["ffmpeg", "-y", "-i", str(video), "-an", "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart", str(output)])


def _concat(parts: list[Path], output: Path) -> None:
    listing = output.parent / f"{output.stem}_concat.txt"
    listing.write_text("".join(f"file '{p.as_posix().replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for p in parts), encoding="utf-8")
    try:
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
              "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
              "-pix_fmt", "yuv420p", "-r", "30", str(output)])
    finally:
        listing.unlink(missing_ok=True)


def process_shots(video: Path, dubbed_audio: Path, output: Path, work_dir: Path, shots: list[dict], provider, face_tracks: list[dict] | None = None) -> dict:
    """Process eligible shots and return a video-only reassembled timeline.

    Real provider failures are fail-closed per shot. The provider runtime
    registry is persisted into the shot manifest for auditability.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    records = []
    if face_tracks is None:
        from face_tracking import track_shot
        face_tracks = []
        for shot in shots:
            idx = int(shot.get("index", 0))
            face_tracks.append({"shot": idx, **track_shot(video, float(shot.get("start", 0)), float(shot.get("end", 0)))})
    by_shot = {int(r.get("shot")): r for r in face_tracks if r.get("shot") is not None}

    for position, shot in enumerate(shots):
        idx = int(shot.get("index", position)); start = float(shot.get("start", 0.0)); end = float(shot.get("end", start))
        source_part = work_dir / f"shot_{idx:05d}_source.mp4"
        _cut(video, start, end, source_part)
        eligibility = by_shot.get(idx, {"eligible": False, "reason": "No face-track record for shot."})
        result = None; chosen = source_part; status = "fallback"
        if eligibility.get("eligible") and provider.available():
            audio_part = work_dir / f"shot_{idx:05d}_audio.wav"; _cut_audio(dubbed_audio, start, end, audio_part)
            processed = work_dir / f"shot_{idx:05d}_lipsync.mp4"
            try:
                result = provider.apply(source_part, audio_part, processed)
                if result.applied and Path(result.output_path).exists():
                    chosen = Path(result.output_path); status = "applied"
            except Exception as exc:
                status = "error"
                records.append({"shot":idx,"start":start,"end":end,"eligible":True,"status":status,
                                "provider":getattr(provider,"name","unknown"),"reason":str(exc)[-1000:],"output":source_part.name})
                parts.append(source_part); continue
        normalized = work_dir / f"shot_{idx:05d}_final.mp4"
        _normalize_video(chosen, normalized)
        parts.append(normalized)
        records.append({"shot":idx,"start":start,"end":end,"eligible":bool(eligibility.get("eligible")),"status":status,
                        "provider":getattr(provider,"name","unknown"),"reason":result.reason if result else eligibility.get("reason","Provider not run."),"output":normalized.name})

    if not parts: raise ValueError("No shots available for reassembly.")
    _concat(parts, output)
    manifest = work_dir / "shot_lipsync_manifest.json"
    manifest.write_text(json.dumps({"version":"1.3","mode":"shot-aware","video_only_reassembly":True,
                                    "records":records,"applied_shots":sum(r["status"]=="applied" for r in records),
                                    "eligible_shots":sum(r["eligible"] for r in records),"total_shots":len(records),
                                    "provider_execution":snapshot()}, indent=2), encoding="utf-8")
    return {"output_path":output,"manifest":manifest,"records":records}

"""Strict post-run certification gate for real Chinese dubbing artifacts.

Certification is deliberately fail-closed. A valid output file alone is not
enough: the manifest must prove real speaker routing, target TTS, applied
lip-sync, passing final QC, and successful provider execution.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

TARGETS = {"Bangla", "English", "Hindi"}
REQUIRED_PROVIDERS = {"stt", "diarization", "translation", "tts", "lip_sync", "final_assembly"}


def _probe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"certification failed: final artifact missing: {path}")
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(r.stdout)
    streams = {s.get("codec_type") for s in data.get("streams", [])}
    duration = float(data.get("format", {}).get("duration") or 0)
    if not {"video", "audio"} <= streams:
        raise RuntimeError("certification failed: final artifact lacks video/audio streams")
    if duration <= 0:
        raise RuntimeError("certification failed: final artifact has invalid duration")
    return {"duration_seconds": duration, "streams": sorted(streams)}


def certify(final_video: Path, manifest: dict[str, Any], *, source_language: str = "Chinese (Simplified)", target_language: str) -> dict[str, Any]:
    if source_language not in {"Chinese (Simplified)", "Chinese (Traditional)"}:
        raise RuntimeError("certification failed: source is not Chinese")
    if target_language not in TARGETS:
        raise RuntimeError(f"certification failed: unsupported target {target_language}")
    artifact = _probe(final_video)
    if (manifest.get("quality_control") or {}).get("status") != "pass":
        raise RuntimeError("certification failed: final QC is not pass")
    if (manifest.get("lip_sync") or {}).get("applied") is not True:
        raise RuntimeError("certification failed: lip-sync was not actually applied")
    shots = manifest.get("shot_qc")
    if not isinstance(shots, dict) or shots.get("status") != "pass":
        raise RuntimeError("certification failed: shot QC evidence is missing or failed")
    segments = manifest.get("segments")
    if not isinstance(segments, list) or not segments:
        raise RuntimeError("certification failed: speaker/character segments are missing")
    if any(not x.get("character") or not x.get("voice") for x in segments):
        raise RuntimeError("certification failed: incomplete speaker routing evidence")
    if any(x.get("timing_lock") is not True for x in segments):
        raise RuntimeError("certification failed: timing-lock evidence is incomplete")
    for segment in segments:
        if not segment.get("reference_audio"):
            raise RuntimeError("certification failed: reference voice evidence is missing")
        reference_qc = segment.get("reference_qc") or {}
        if reference_qc.get("status") != "SUCCEEDED":
            raise RuntimeError("certification failed: reference voice QC is not successful")
        score = segment.get("reference_selection_score")
        if not isinstance(score, (list, tuple)) or len(score) != 3:
            raise RuntimeError("certification failed: reference selection evidence is incomplete")
    providers = manifest.get("provider_execution") or {}
    if not isinstance(providers, dict):
        raise RuntimeError("certification failed: provider manifest is missing")
    missing = sorted(REQUIRED_PROVIDERS - set(providers))
    if missing:
        raise RuntimeError("certification failed: missing providers: " + ", ".join(missing))
    invalid = [name for name in REQUIRED_PROVIDERS if providers[name].get("state") != "succeeded" or providers[name].get("applied") is not True]
    if invalid:
        raise RuntimeError("certification failed: provider evidence not succeeded/applied: " + ", ".join(sorted(invalid)))
    return {"certified": True, "source_language": source_language, "target_language": target_language, "artifact": artifact, "lip_sync_applied": True, "final_qc": "pass", "providers": sorted(REQUIRED_PROVIDERS), "segment_count": len(segments)}


def certify_manifest_file(video: Path, manifest_path: Path, **kwargs) -> dict[str, Any]:
    return certify(video, json.loads(manifest_path.read_text(encoding="utf-8")), **kwargs)

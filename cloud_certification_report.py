"""Build conservative cloud-run reports from certification and manifest evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _exists(path: str | Path | None) -> bool:
    return bool(path) and Path(path).is_file()


def build_cloud_report(
    *,
    certification: dict[str, Any],
    manifest: dict[str, Any],
    artifacts: dict[str, str | Path | None],
    runtime_stt_provider: str = "local-whisper",
    stt_model: str = "large-v3",
    runtime_tts_provider: str = "xtts-v2",
) -> dict[str, Any]:
    """Return a report that never upgrades missing/failed evidence into success claims."""
    certified = certification.get("certified") is True
    paths = {name: str(path) if _exists(path) else None for name, path in artifacts.items()}
    evidence = manifest if certified else {}
    quality = evidence.get("quality_control") or {}
    lip_sync = evidence.get("lip_sync") or {}
    music = evidence.get("music") or {}

    return {
        "status": "certified" if certified else "failed_closed",
        "certification": certification,
        "artifacts": paths,
        "output_sha256": certification.get("artifact_sha256") if certified else None,
        "claims": {
            "original_dialogue_removed": evidence.get("original_dialogue_in_final") is False if certified else "unknown",
            "original_music_removed": evidence.get("background_preserved") is False and music.get("enabled") is False if certified else "unknown",
            "lip_sync_applied": lip_sync.get("applied") is True if certified else "not_certified",
            "final_qc": quality.get("status") if certified else "not_certified",
            "reference_voice_cloning": evidence.get("reference_voice_cloning") is True if certified else "not_certified",
            "speaker_routing": "validated" if certified and evidence.get("segments") else "not_certified",
        },
        "providers": {
            "stt_adapter": runtime_stt_provider,
            "stt_model": stt_model,
            "tts_adapter": runtime_tts_provider,
            "manifest_stt_provider": evidence.get("stt_provider") if certified else None,
            "manifest_tts_provider": evidence.get("tts_provider") if certified else None,
        },
    }

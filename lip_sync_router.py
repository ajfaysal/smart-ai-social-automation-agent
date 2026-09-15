"""Route lip-sync work by scene and provider capability."""
from __future__ import annotations

from pathlib import Path

from lip_sync_provider import get_lip_sync_provider
from scene_analysis import build_scene_manifest


def route_lip_sync(video_path: Path, dubbed_audio: Path, output_path: Path, work_dir: Path):
    provider = get_lip_sync_provider()
    scene_manifest = work_dir / "scene_manifest.json"
    build_scene_manifest(video_path, scene_manifest)

    if not provider.available():
        return {
            "output_path": video_path,
            "applied": False,
            "provider": provider.name,
            "reason": "Real lip-sync provider is not configured; original video frames retained.",
            "scene_manifest": scene_manifest,
        }

    result = provider.apply(video_path, dubbed_audio, output_path)
    return {
        "output_path": result.output_path,
        "applied": result.applied,
        "provider": result.provider,
        "reason": result.reason,
        "scene_manifest": scene_manifest,
    }

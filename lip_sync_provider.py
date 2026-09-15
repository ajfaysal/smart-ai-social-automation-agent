"""Configurable real-video lip-sync provider boundary with execution audit."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from provider_runtime import finalize


@dataclass(frozen=True)
class LipSyncResult:
    output_path: Path
    applied: bool
    provider: str
    reason: str


class LipSyncProvider:
    name = "base"

    def available(self) -> bool:
        return False

    def apply(self, video_path: Path, audio_path: Path, output_path: Path) -> LipSyncResult:
        raise NotImplementedError


class DisabledLipSyncProvider(LipSyncProvider):
    name = "disabled"

    def apply(self, video_path: Path, audio_path: Path, output_path: Path) -> LipSyncResult:
        finalize(self.name, configured=False, attempted=False, reason="No real lip-sync engine is configured.")
        return LipSyncResult(video_path, False, self.name, "No real lip-sync engine is configured.")


class Wav2LipProvider(LipSyncProvider):
    """Adapter for a locally installed Wav2Lip command wrapper.

    The wrapper path and model are supplied through environment variables so
    model weights are never bundled into this repository.
    """
    name = "wav2lip"

    def __init__(self):
        self.command = os.getenv("WAV2LIP_COMMAND", "wav2lip")
        self.model = os.getenv("WAV2LIP_MODEL_PATH", "")

    def available(self) -> bool:
        return bool(shutil.which(self.command) and self.model and Path(self.model).is_file())

    def apply(self, video_path: Path, audio_path: Path, output_path: Path) -> LipSyncResult:
        configured = bool(self.model)
        if not self.available():
            reason = "Wav2Lip command/model is not configured."
            finalize(self.name, configured=configured, attempted=False, reason=reason,
                     capabilities=["video_lip_sync"])
            return LipSyncResult(video_path, False, self.name, reason)
        try:
            command = [
                self.command, "--video", str(video_path), "--audio", str(audio_path),
                "--checkpoint", self.model, "--outfile", str(output_path),
            ]
            completed = subprocess.run(command, capture_output=True, text=True)
            if completed.returncode != 0:
                reason = completed.stderr[-4000:] or "Wav2Lip execution failed."
                finalize(self.name, configured=True, attempted=True, reason=reason,
                         capabilities=["video_lip_sync"])
                raise RuntimeError(reason)
            execution = finalize(self.name, configured=True, attempted=True,
                                 artifact=output_path, min_bytes=1024, suffix=".mp4",
                                 capabilities=["video_lip_sync"])
            if not execution.applied:
                raise RuntimeError(f"Wav2Lip artifact validation failed: {execution.reason}")
            return LipSyncResult(output_path, True, self.name, "Real video lip-sync applied and artifact validated.")
        except Exception:
            raise


def get_lip_sync_provider() -> LipSyncProvider:
    provider = os.getenv("LIPSYNC_PROVIDER", "disabled").strip().lower()
    if provider == "wav2lip":
        return Wav2LipProvider()
    return DisabledLipSyncProvider()

"""Configurable real-video lip-sync provider boundary.

The default provider is disabled unless a real engine is explicitly configured.
This prevents the application from claiming lip-sync when it has only achieved
voice timing alignment.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


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
        if not self.available():
            return LipSyncResult(video_path, False, self.name, "Wav2Lip command/model is not configured.")
        command = [
            self.command,
            "--video", str(video_path),
            "--audio", str(audio_path),
            "--checkpoint", self.model,
            "--outfile", str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr[-4000:] or "Wav2Lip execution failed.")
        if not output_path.exists():
            raise RuntimeError("Wav2Lip completed without producing an output video.")
        return LipSyncResult(output_path, True, self.name, "Real video lip-sync applied.")


def get_lip_sync_provider() -> LipSyncProvider:
    provider = os.getenv("LIPSYNC_PROVIDER", "disabled").strip().lower()
    if provider == "wav2lip":
        return Wav2LipProvider()
    return DisabledLipSyncProvider()

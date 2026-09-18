"""Auditable Demucs source-separation provider boundary."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from provider_runtime import finalize


def _run_separation(source_audio: Path, work_dir: Path) -> tuple[Path, Path]:
    demucs = shutil.which("demucs")
    if not demucs:
        finalize(
            "demucs",
            configured=False,
            attempted=False,
            reason="Demucs command is not installed.",
            capabilities=["two_stem_source_separation"],
        )
        raise RuntimeError("Demucs source separation is not installed on the server.")

    out_dir = work_dir / "separated"
    out_dir.mkdir(exist_ok=True)
    completed = subprocess.run(
        [demucs, "--two-stems=vocals", "-o", str(out_dir), str(source_audio)],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        reason = completed.stderr[-4000:] or "Demucs execution failed."
        finalize("demucs", configured=True, attempted=True, reason=reason,
                 capabilities=["two_stem_source_separation"])
        raise RuntimeError(reason)

    vocals = next(iter(out_dir.rglob("vocals.wav")), None)
    no_vocals = next(iter(out_dir.rglob("no_vocals.wav")), None)
    if not vocals or not no_vocals:
        reason = "Demucs completed but both vocals.wav and no_vocals.wav are required."
        finalize("demucs", configured=True, attempted=True, reason=reason,
                 capabilities=["two_stem_source_separation"])
        raise RuntimeError(reason)
    return vocals, no_vocals


def separate(source_audio: Path, work_dir: Path) -> Path:
    """Return the validated no-vocals/background stem."""
    vocals, background = _run_separation(source_audio, work_dir)
    execution = finalize(
        "demucs", configured=True, attempted=True, artifact=background,
        min_bytes=1024, suffix=".wav",
        capabilities=["two_stem_source_separation"],
    )
    if not execution.applied:
        raise RuntimeError(f"Demucs artifact validation failed: {execution.reason}")
    return background


def separate_vocals(source_audio: Path, work_dir: Path) -> Path:
    """Return the validated dialogue/vocals stem for diarization and STT."""
    vocals, background = _run_separation(source_audio, work_dir)
    execution = finalize(
        "demucs", configured=True, attempted=True, artifact=vocals,
        min_bytes=1024, suffix=".wav",
        capabilities=["two_stem_source_separation"],
    )
    if not execution.applied:
        raise RuntimeError(f"Demucs vocals artifact validation failed: {execution.reason}")
    return vocals

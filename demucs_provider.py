"""Auditable Demucs source-separation provider boundary."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from provider_runtime import finalize


def separate(source_audio: Path, work_dir: Path) -> Path:
    demucs = shutil.which("demucs")
    if not demucs:
        finalize("demucs", configured=False, attempted=False,
                 reason="Demucs command is not installed.",
                 capabilities=["two_stem_source_separation"])
        raise RuntimeError("Background preservation requires Demucs source separation to be installed on the server.")

    out_dir = work_dir / "separated"
    out_dir.mkdir(exist_ok=True)
    try:
        completed = subprocess.run(
            [demucs, "--two-stems=vocals", "-o", str(out_dir), str(source_audio)],
            capture_output=True, text=True,
        )
        if completed.returncode != 0:
            reason = completed.stderr[-4000:] or "Demucs execution failed."
            finalize("demucs", configured=True, attempted=True, reason=reason,
                     capabilities=["two_stem_source_separation"])
            raise RuntimeError(reason)

        candidates = list(out_dir.rglob("no_vocals.wav"))
        if not candidates:
            reason = "Demucs completed but no no_vocals.wav artifact was produced."
            finalize("demucs", configured=True, attempted=True, reason=reason,
                     capabilities=["two_stem_source_separation"])
            raise RuntimeError(reason)

        source = candidates[0]
        execution = finalize(
            "demucs", configured=True, attempted=True, artifact=source,
            min_bytes=1024, suffix=".wav",
            capabilities=["two_stem_source_separation"],
        )
        if not execution.applied:
            raise RuntimeError(f"Demucs artifact validation failed: {execution.reason}")
        return source
    except RuntimeError:
        raise
    except Exception as exc:
        reason = f"Demucs execution error: {exc}"
        finalize("demucs", configured=True, attempted=True, reason=reason,
                 capabilities=["two_stem_source_separation"])
        raise RuntimeError(reason) from exc

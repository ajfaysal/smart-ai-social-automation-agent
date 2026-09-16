"""Preflight checks for a real Chinese-drama dubbing run.

This module is deliberately side-effect free: it validates the selected V1
language pair and the runtime prerequisites before a GPU notebook starts an
expensive inference job.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse

from v1_scope import V1LanguageSelection, validate_v1_selection


@dataclass(frozen=True)
class RealRunPreflight:
    selection: V1LanguageSelection
    video_url: str
    requires_openai: bool
    requires_wav2lip_checkpoint: bool
    missing_secrets: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return bool(self.video_url) and not self.missing_secrets


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def build_preflight(
    *,
    video_url: str,
    source_language: str = "Chinese (Simplified)",
    target_language: str = "Bangla",
    require_openai: bool = True,
    require_wav2lip: bool = True,
) -> RealRunPreflight:
    selection = validate_v1_selection(source_language, target_language)
    video_url = str(video_url).strip()
    if not _is_http_url(video_url):
        raise ValueError("Real-run video_url must be a valid HTTP(S) URL.")

    required = []
    if require_openai:
        required.append("OPENAI_API_KEY")
    if require_wav2lip:
        required.extend(("WAV2LIP_CHECKPOINT_URL", "WAV2LIP_S3FD_URL"))
    missing = tuple(name for name in required if not os.getenv(name, "").strip())
    return RealRunPreflight(
        selection=selection,
        video_url=video_url,
        requires_openai=require_openai,
        requires_wav2lip_checkpoint=require_wav2lip,
        missing_secrets=missing,
    )

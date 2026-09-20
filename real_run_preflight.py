"""Preflight checks for a real Chinese-drama dubbing run."""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
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
    missing_runtime: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return bool(self.video_url) and not self.missing_secrets and not self.missing_runtime


def _is_public_http_url(value: str) -> bool:
    parsed = urlparse(str(value).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    if parsed.username or parsed.password:
        return False
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname or hostname in {"localhost", "localhost.localdomain"}:
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast)


def _is_http_url(value: str) -> bool:
    return _is_public_http_url(value)


def selected_text_provider() -> tuple[str, str]:
    """Return configured text provider and its required API-key environment name."""
    provider = os.getenv("DUBBING_TEXT_PROVIDER", "openai").strip().lower()
    keys = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}
    if provider not in keys:
        raise ValueError(f"Unsupported DUBBING_TEXT_PROVIDER: {provider}")
    return provider, keys[provider]


def build_preflight(
    *,
    video_url: str,
    source_language: str = "Chinese (Simplified)",
    target_language: str = "Bangla",
    require_openai: bool = True,
    require_wav2lip: bool = True,
    require_diarization: bool = True,
    diarization_backend: str = "pyannote",
    require_reference_voice: bool = False,
    require_whisper_xtts: bool = False,
) -> RealRunPreflight:
    selection = validate_v1_selection(source_language, target_language)
    video_url = str(video_url).strip()
    if not _is_public_http_url(video_url):
        raise ValueError("Real-run video_url must be a public HTTP(S) URL.")

    required = []
    if require_openai:
        _, provider_key = selected_text_provider()
        required.append(provider_key)
    if require_wav2lip:
        required.extend(("WAV2LIP_CHECKPOINT_URL", "WAV2LIP_S3FD_URL"))
    missing = tuple(name for name in required if not os.getenv(name, "").strip())

    runtime = []
    if require_wav2lip:
        for name in ("WAV2LIP_CHECKPOINT_URL", "WAV2LIP_S3FD_URL"):
            value = os.getenv(name, "").strip()
            if value and not _is_public_http_url(value):
                runtime.append(f"invalid {name}")
    if require_whisper_xtts:
        if not os.getenv("WHISPER_LOCAL_COMMAND", "").strip():
            runtime.append("WHISPER_LOCAL_COMMAND")
        if not os.getenv("XTTS_V2_TTS_COMMAND", "").strip():
            runtime.append("XTTS_V2_TTS_COMMAND")
    if require_reference_voice:
        reference_keys = (
            "BANGLA_REFERENCE_TTS_COMMAND",
            "COSYVOICE_TTS_COMMAND",
            "FISH_SPEECH_TTS_COMMAND",
            "GPT_SOVITS_TTS_COMMAND",
            "OPENVOICE_TTS_COMMAND",
        )
        if not any(os.getenv(name, "").strip() for name in reference_keys):
            runtime.append("REFERENCE_TTS_ENGINE_COMMAND")
    if require_diarization:
        env_name = {
            "pyannote": "PYANNOTE_DIARIZATION_COMMAND",
            "3d-speaker": "THREE_D_SPEAKER_DIARIZATION_COMMAND",
        }.get(diarization_backend)
        if not env_name:
            runtime.append(f"unsupported diarization backend: {diarization_backend}")
        elif not os.getenv(env_name, "").strip():
            runtime.append(env_name)
    return RealRunPreflight(
        selection,
        video_url,
        require_openai,
        require_wav2lip,
        missing,
        tuple(runtime),
    )

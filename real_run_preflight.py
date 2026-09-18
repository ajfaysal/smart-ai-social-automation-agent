"""Preflight checks for a real Chinese-drama dubbing run."""
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
    missing_runtime: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return bool(self.video_url) and not self.missing_secrets and not self.missing_runtime

def _is_http_url(value: str) -> bool:
    parsed=urlparse(value)
    return parsed.scheme in {"http","https"} and bool(parsed.netloc)

def build_preflight(*, video_url: str, source_language: str="Chinese (Simplified)",
                    target_language: str="Bangla", require_openai: bool=True,
                    require_wav2lip: bool=True, require_diarization: bool=True,
                    diarization_backend: str="pyannote") -> RealRunPreflight:
    selection=validate_v1_selection(source_language,target_language)
    video_url=str(video_url).strip()
    if not _is_http_url(video_url):
        raise ValueError("Real-run video_url must be a valid HTTP(S) URL.")
    required=[]
    if require_openai: required.append("OPENAI_API_KEY")
    if require_wav2lip: required.extend(("WAV2LIP_CHECKPOINT_URL","WAV2LIP_S3FD_URL"))
    missing=tuple(name for name in required if not os.getenv(name,"").strip())
    runtime=[]
    if require_diarization:
        env_name={"pyannote":"PYANNOTE_DIARIZATION_COMMAND","3d-speaker":"THREE_D_SPEAKER_DIARIZATION_COMMAND"}.get(diarization_backend)
        if not env_name:
            runtime.append(f"unsupported diarization backend: {diarization_backend}")
        elif not os.getenv(env_name,"").strip():
            runtime.append(env_name)
    return RealRunPreflight(selection,video_url,require_openai,require_wav2lip,missing,tuple(runtime))

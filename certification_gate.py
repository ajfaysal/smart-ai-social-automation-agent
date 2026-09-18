"""Fail-closed certification gate for real multilingual drama runs."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any

@dataclass(frozen=True)
class CertificationGate:
    ready: bool
    reasons: tuple[str, ...]

REQUIRED_SUCCESSES=("source_download","stt","diarization","speaker_routing","tts","demucs","final_assembly","final_qc")

def evaluate_certification_gate(manifest: Mapping[str, Any]) -> CertificationGate:
    reasons=[]
    providers=manifest.get("provider_execution") or {}
    for name in REQUIRED_SUCCESSES:
        entry=providers.get(name)
        if isinstance(entry,dict):
            status=str(entry.get("status","")).upper()
        else:
            status=""
        if status != "SUCCEEDED":
            reasons.append(f"{name}: expected SUCCEEDED")
    if not manifest.get("output_exists",False):
        reasons.append("output_exists: expected true")
    if not manifest.get("lip_sync",{}).get("applied",False):
        reasons.append("lip_sync: expected applied")
    if not manifest.get("quality_control",{}).get("valid",False):
        reasons.append("quality_control: expected valid")
    return CertificationGate(not reasons,tuple(reasons))

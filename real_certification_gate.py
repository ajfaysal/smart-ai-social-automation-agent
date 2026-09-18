"""Fail-closed certification gate for real multilingual dubbing runs."""
from __future__ import annotations
from pathlib import Path
import json
import subprocess

REQUIRED_LANGUAGES={"Bangla","English","Hindi"}

def certify_real_run(manifest_path: Path, expected_language: str, output_path: Path) -> dict:
    if expected_language not in REQUIRED_LANGUAGES:
        raise ValueError("Certification target must be Bangla, English, or Hindi.")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Certification failed: final video artifact is missing.")
    data=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if str(data.get("target_language") or expected_language) != expected_language:
        raise RuntimeError("Certification failed: target language mismatch.")
    qc=data.get("quality_control") or {}
    if qc.get("status") != "pass":
        raise RuntimeError("Certification failed: final QC did not pass.")
    lip=data.get("lip_sync") or {}
    if lip.get("applied") is not True:
        raise RuntimeError("Certification failed: lip-sync was not applied.")
    identities=data.get("speaker_identity") or {}
    if identities.get("status") != "SUCCEEDED":
        raise RuntimeError("Certification failed: speaker identity did not succeed.")
    routes=data.get("speaker_routes") or []
    if not routes or any(str(x.get("routing_status")) != "SUCCEEDED" for x in routes):
        raise RuntimeError("Certification failed: speaker routing is incomplete.")
    providers=data.get("provider_execution") or []
    if not providers:
        raise RuntimeError("Certification failed: provider execution manifest is missing.")
    bad=[x for x in providers if x.get("state") not in {"succeeded","skipped"} or (x.get("applied") and x.get("state")!="succeeded")]
    if bad:
        raise RuntimeError("Certification failed: provider execution contains an invalid or failed applied step.")
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type","-of","json",str(output_path)],capture_output=True,text=True,check=True)
    kinds={x.get("codec_type") for x in json.loads(probe.stdout).get("streams",[])}
    if not {"video","audio"} <= kinds:
        raise RuntimeError("Certification failed: output must contain video and audio.")
    return {"certified":True,"target_language":expected_language,"output":str(output_path),"qc_status":"pass","lip_sync_applied":True,"speaker_identity":"SUCCEEDED","speaker_routes":"SUCCEEDED"}

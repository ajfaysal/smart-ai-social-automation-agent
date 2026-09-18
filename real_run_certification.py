"""Strict certification gate for real GPU dubbing artifacts."""
from __future__ import annotations
import json
from pathlib import Path

REQUIRED = ("output","manifest","subtitle","text_cleanup_report","speaker_identity_manifest","speaker_routing_manifest")

def validate_certification(report_path: Path) -> dict:
    report=json.loads(Path(report_path).read_text(encoding="utf-8"))
    errors=[]
    for key in REQUIRED:
        value=report.get(key)
        if not value or not Path(value).exists():
            errors.append(f"missing artifact: {key}")
    if report.get("status") != "certified":
        errors.append("run status is not certified")
    if report.get("speaker_identity_status") != "SUCCEEDED":
        errors.append("speaker identity did not succeed")
    if int(report.get("speaker_count",0)) < 1:
        errors.append("no speakers certified")
    if not report.get("speaker_routing"):
        errors.append("speaker routing evidence missing")
    lip=report.get("lip_sync") or {}
    if not lip.get("applied"):
        errors.append("lip-sync was not applied")
    if report.get("audio_mix") != "replacement-dialogue-only-no-original-music":
        errors.append("unexpected audio mix policy")
    report["certification_errors"]=errors
    report["certified"]=not errors
    return report

def write_certification_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

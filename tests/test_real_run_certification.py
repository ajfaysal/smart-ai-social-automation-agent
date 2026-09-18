from pathlib import Path
from real_run_certification import validate_certification

def test_certification_rejects_missing_and_unapplied_lipsync(tmp_path):
    report=tmp_path/"report.json"
    report.write_text("""{"status":"failed_closed","output":"","manifest":"","subtitle":"","text_cleanup_report":"","speaker_identity_manifest":"","speaker_routing_manifest":"","speaker_identity_status":"FAILED","speaker_count":0,"lip_sync":{"applied":false},"audio_mix":"replacement-dialogue-only-no-original-music"}""")
    result=validate_certification(report)
    assert result["certified"] is False
    assert any("lip-sync" in x for x in result["certification_errors"])

def test_certification_accepts_complete_contract(tmp_path):
    paths={}
    for key in ("output","manifest","subtitle","text_cleanup_report","speaker_identity_manifest","speaker_routing_manifest"):
        p=tmp_path/key; p.write_text("artifact"); paths[key]=str(p)
    report=tmp_path/"report.json"
    payload={**paths,"status":"certified","speaker_identity_status":"SUCCEEDED","speaker_count":2,"speaker_routing":"diarized-speaker-to-character-to-voice-profile/reference-audio","lip_sync":{"applied":True},"audio_mix":"replacement-dialogue-only-no-original-music"}
    import json
    report.write_text(json.dumps(payload))
    result=validate_certification(report)
    assert result["certified"] is True

import json
import pytest
from pathlib import Path
from real_certification_gate import certify_real_run

def base(tmp_path, **overrides):
    data={"target_language":"Bangla","quality_control":{"status":"pass"},"lip_sync":{"applied":True},"speaker_identity":{"status":"SUCCEEDED"},"speaker_routes":[{"routing_status":"SUCCEEDED"}],"provider_execution":[{"state":"succeeded","applied":True}]}
    data.update(overrides)
    m=tmp_path/"manifest.json"; m.write_text(json.dumps(data),encoding="utf-8")
    v=tmp_path/"out.mp4"; v.write_bytes(b"x")
    return m,v

def test_certifies_only_when_all_evidence_is_valid(tmp_path, monkeypatch):
    m,v=base(tmp_path)
    monkeypatch.setattr("real_certification_gate.subprocess.run",lambda *a,**k:type("R",(),{"stdout":'{"streams":[{"codec_type":"video"},{"codec_type":"audio"}]}'} )())
    result=certify_real_run(m,"Bangla",v)
    assert result["certified"] is True

@pytest.mark.parametrize("field, value", [
    ("lip_sync", {"applied":False}),
    ("speaker_identity", {"status":"FAILED"}),
    ("speaker_routes", [{"routing_status":"FAILED"}]),
    ("quality_control", {"status":"fail"}),
])
def test_certification_fails_closed(tmp_path, monkeypatch, field, value):
    m,v=base(tmp_path,**{field:value})
    monkeypatch.setattr("real_certification_gate.subprocess.run",lambda *a,**k:type("R",(),{"stdout":'{"streams":[{"codec_type":"video"},{"codec_type":"audio"}]}'} )())
    with pytest.raises(RuntimeError):
        certify_real_run(m,"Bangla",v)

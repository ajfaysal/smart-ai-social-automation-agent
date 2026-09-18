from certification_gate import evaluate_certification_gate

def test_gate_rejects_incomplete_real_run():
    result=evaluate_certification_gate({})
    assert not result.ready
    assert "lip_sync: expected applied" in result.reasons

def test_gate_accepts_complete_real_run():
    providers={k:{"status":"SUCCEEDED"} for k in ("source_download","stt","diarization","speaker_routing","tts","demucs","final_assembly","final_qc")}
    result=evaluate_certification_gate({"provider_execution":providers,"output_exists":True,"lip_sync":{"applied":True},"quality_control":{"valid":True}})
    assert result.ready
    assert result.reasons==()

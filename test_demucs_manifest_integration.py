from pathlib import Path


def test_demucs_audit_contract_has_expected_states():
    source = Path("demucs_provider.py").read_text(encoding="utf-8")
    assert "finalize(\"demucs\"" in source
    assert "no_vocals.wav" in source
    assert "min_bytes=1024" in source
    assert "suffix=\".wav\"" in source

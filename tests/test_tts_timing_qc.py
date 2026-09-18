from pathlib import Path
import wave
import pytest
from tts_timing_qc import validate_timing_lock

def _wav(path: Path, seconds: float):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b"\x00\x00" * int(8000 * seconds))

def test_accepts_exact_timing_and_reports_drift(tmp_path):
    p=tmp_path/"fit.wav"; _wav(p, 1.0)
    result=validate_timing_lock(p, 1.0)
    assert result["timing_lock"] is True
    assert result["drift_ms"] == pytest.approx(0, abs=1)

def test_rejects_timing_drift(tmp_path):
    p=tmp_path/"fit.wav"; _wav(p, 1.10)
    with pytest.raises(RuntimeError, match="timing lock drift"):
        validate_timing_lock(p, 1.0)

def test_rejects_excessive_acceleration(tmp_path):
    raw=tmp_path/"raw.wav"; fit=tmp_path/"fit.wav"
    _wav(raw, 2.1); _wav(fit, 1.0)
    with pytest.raises(RuntimeError, match="excessive acceleration"):
        validate_timing_lock(fit, 1.0, raw_path=raw)

def test_accepts_slow_or_padded_source(tmp_path):
    raw=tmp_path/"raw.wav"; fit=tmp_path/"fit.wav"
    _wav(raw, 0.4); _wav(fit, 1.0)
    result=validate_timing_lock(fit, 1.0, raw_path=raw)
    assert result["speed_ratio"] == pytest.approx(0.4, abs=0.02)

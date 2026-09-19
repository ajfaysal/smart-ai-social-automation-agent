import pytest

import drama_dubbing
from voice_engine_registry import VOICE_ENGINES, engine_capability


def test_xtts_v2_is_reference_capable():
    assert "xtts-v2" in VOICE_ENGINES
    assert VOICE_ENGINES["xtts-v2"].supports_reference_voice is True
    assert engine_capability("xtts-v2")["supports_cross_lingual"] is True


def test_local_whisper_requires_command(monkeypatch, tmp_path):
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"audio")
    monkeypatch.setenv("DUBBING_STT_PROVIDER", "local-whisper")
    monkeypatch.delenv("WHISPER_LOCAL_COMMAND", raising=False)
    with pytest.raises(RuntimeError, match="WHISPER_LOCAL_COMMAND"):
        drama_dubbing.transcribe(audio)


def test_local_whisper_accepts_verbose_json(monkeypatch, tmp_path):
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"audio")
    command = (
        "python -c "
        "\"import json; json.dump({'segments':[{'start':0,'end':1,'text':'hello'}]}, open(r'{output}','w'))\""
    )
    monkeypatch.setenv("DUBBING_STT_PROVIDER", "local-whisper")
    monkeypatch.setenv("WHISPER_LOCAL_COMMAND", command)
    result = drama_dubbing.transcribe(audio)
    assert result["segments"][0]["text"] == "hello"

from pathlib import Path
import wave


def test_bangla_make_tts_uses_reference_aware_provider(monkeypatch, tmp_path):
    import drama_dubbing
    calls = {}
    def fake_synthesize(text, out_path, **kwargs):
        calls.update(kwargs)
        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\x00\x10" * 32000)
    monkeypatch.setattr("tts_provider.synthesize_bangla", fake_synthesize)
    out = tmp_path / "voice.wav"
    drama_dubbing.make_tts("হ্যালো", out, "bn_c01_f_young", "sad", character_id="C01", reference_audio="/runtime/C01.wav", target_language="Bangla")
    assert calls["character_id"] == "C01"
    assert calls["reference_audio"] == "/runtime/C01.wav"

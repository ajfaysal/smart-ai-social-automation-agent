"""Deterministic end-to-end orchestration test for the dubbing pipeline.

External APIs, media processors, and lip-sync providers are replaced with
small fakes so CI validates the complete control flow without credentials or
large model weights.
"""
from pathlib import Path
import tempfile
from unittest.mock import patch

import drama_dubbing as app


def test_end_to_end_dubbing_orchestration():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        source = work / "source.mp4"
        source.write_bytes(b"fake-video")

        prepared = work / "prepared.mp4"
        final_audio = work / "master.wav"
        dubbed = work / "dubbed.wav"
        concat = work / "concat.txt"

        def fake_run(cmd):
            out = Path(cmd[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.suffix in {".wav", ".mp3", ".mp4"}:
                out.write_bytes(b"fake-media")
            return ""

        def fake_duration(path):
            return 4.0

        def fake_transcribe(_):
            return {"segments": [
                {"start": 0.0, "end": 1.5, "text": "Hello there."},
                {"start": 2.0, "end": 4.0, "text": "I am very happy to see you."},
            ]}

        def fake_plan(_):
            return {
                0: {"character": "C1", "profile": "female", "emotion": "happy"},
                1: {"character": "C2", "profile": "male", "emotion": "romantic"},
            }

        def fake_translate(text, language, seconds, emotion):
            assert language == "Chinese (Simplified)"
            assert seconds > 0 and emotion in {"happy", "romantic"}
            return "你好" if "Hello" in text else "见到你很开心"

        def fake_tts(text, out, voice, emotion, **kwargs):
            assert text and voice and emotion
            out.write_bytes(b"tts")

        def fake_fit(src, out, target):
            assert src.exists() and target > 0
            out.write_bytes(b"fit")

        def fake_timeline(items, total, workdir):
            assert len(items) == 2 and total == 4.0
            concat.write_text("timeline", encoding="utf-8")
            return concat

        def fake_master(background, dub, music, total, workdir):
            assert dub.exists() and music is not None and total == 4.0
            final_audio.write_bytes(b"master")
            return final_audio

        def fake_attach(video, audio, out, total):
            assert video.exists() and audio.exists() and total == 4.0
            out.write_bytes(b"final-video" + b"x" * 2048)

        def fake_music(manifest, total, workdir):
            assert len(manifest) == 2 and total == 4.0
            music = workdir / "mood_music.wav"
            music.write_bytes(b"music")
            return music, "happy"

        def fake_lip_plan(manifest, out):
            assert len(manifest) == 2
            out.write_text("{}", encoding="utf-8")

        class DisabledProvider:
            name = "disabled"
            def available(self):
                return False

        class DisabledLandmark:
            name = "disabled"
            def available(self):
                return False

        with patch.object(app, "duration", fake_duration), \
             patch.object(app, "run", fake_run), \
             patch.object(app, "separate_background", lambda _a, _w: None), \
             patch.object(app, "transcribe", fake_transcribe), \
             patch.object(app, "director_plan", fake_plan), \
             patch.object(app, "translate", fake_translate), \
             patch.object(app, "make_tts", fake_tts), \
             patch.object(app, "fit_audio_exact", fake_fit), \
             patch.object(app, "build_timeline", fake_timeline), \
             patch.object(app, "build_mood_music", fake_music), \
             patch.object(app, "master_mix", fake_master), \
             patch.object(app, "attach_audio", fake_attach), \
             patch.object(app, "build_lip_sync_plan", fake_lip_plan), \
             patch.object(app, "get_lip_sync_provider", lambda: DisabledProvider()), \
             patch.object(app, "get_landmark_provider", lambda: DisabledLandmark()), \
             patch.object(app, "validate_output", lambda *args, **kwargs: {"status": "pass"}):
            output, mood, lip = app.dub_video(
                source, "Chinese (Simplified)", requested_voice="auto",
                preserve_background=False, add_mood_music=True, lip_sync=True,
            )

        assert output.exists()
        assert mood == "happy"
        assert lip["applied"] is False
        assert lip["provider"] == "disabled"
        manifest = Path(app.OUTPUT_DIR) / f"{output.stem}.json"
        assert manifest.exists()
        data = manifest.read_text(encoding="utf-8")
        assert "original_dialogue_in_final" in data
        assert "C1" in data and "C2" in data
        output.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        (Path(app.OUTPUT_DIR) / f"{output.stem}.srt").unlink(missing_ok=True)

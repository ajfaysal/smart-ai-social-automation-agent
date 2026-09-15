# Drama Dubbing Tool

A small FastAPI web app for audiovisual drama dubbing.

## Pipeline

1. Upload a video.
2. Extract speech with OpenAI transcription.
3. Translate each dialogue segment into the selected language.
4. Generate TTS audio for each segment.
5. Time-fit segments to the original dialogue windows.
6. Replace the original audio while keeping the original video stream.

## Run

Install dependencies and ensure `ffmpeg`/`ffprobe` are installed.

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_key
uvicorn drama_dubbing:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

Environment variables can override the default transcription, translation, and TTS models: `DUBBING_STT_MODEL`, `DUBBING_TRANSLATION_MODEL`, and `DUBBING_TTS_MODEL`.

## Notes

This MVP replaces the source dialogue audio. A production version should add speaker diarization, voice assignment per character, background-music/SFX separation, subtitle export, job queues, progress reporting, authentication, file-size limits, and automatic cleanup.

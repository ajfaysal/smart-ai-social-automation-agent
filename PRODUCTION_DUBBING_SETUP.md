# Production Dubbing Setup

## 1. System dependencies

Install Python dependencies from `requirements.txt`, plus `ffmpeg` and `ffprobe` on the server.

## 2. Environment

Copy `.env.example` to `.env` or export the variables in the process environment. Set `OPENAI_API_KEY` before starting the API.

## 3. Background preservation

When `preserve_background=true`, Demucs is required. The pipeline fails closed if Demucs is unavailable so the original dialogue is not accidentally retained beneath the new dub.

`--two-stems=vocals` is a practical separation baseline, not perfect dialogue isolation. It can affect sung vocals and may introduce separation artifacts.

## 4. Lip-sync

Lip-sync is opt-in. Set all of the following for the configured provider path:

- `LIPSYNC_PROVIDER` — for example `wav2lip`
- `WAV2LIP_COMMAND`
- `WAV2LIP_MODEL_PATH`
- `FACE_DETECTOR=opencv` (or another supported detector)
- `MOUTH_LANDMARK_PROVIDER=mediapipe` (or the explicit Haar mouth fallback)

MediaPipe landmark detection only validates facial/mouth geometry; it does not animate the mouth. An actual animation provider/model is required for visual lip-sync.

Shots that fail face/mouth eligibility safely retain the source visual and still use the timing-locked final audio.

## 5. Quality expectations

The pipeline validates final streams, duration drift, segment timing, and shot continuity. These checks do not guarantee subjective dubbing quality, perfect speaker identity, perfect translation, or indistinguishable lip motion.

For production, review representative clips containing profile faces, occlusion, rapid cuts, multiple speakers, singing, shouting, and low-resolution footage before enabling automatic delivery.

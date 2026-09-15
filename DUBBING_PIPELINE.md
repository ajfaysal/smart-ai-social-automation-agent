# DubStudio AI — Production Dubbing Pipeline

## Pipeline

1. Extract source dialogue/transcript with timestamps.
2. Treat the source dialogue window as the master clock.
3. Build a director plan with stable character IDs and emotion labels.
4. Translate/adapt each line for natural spoken delivery while respecting its duration.
5. Generate character-consistent TTS with emotion-directed acting instructions.
6. Time-fit every generated clip with FFmpeg and verify drift.
7. Assemble the complete dialogue timeline, preserving silence between lines.
8. Separate original vocals/dialogue with Demucs when background preservation is enabled; fail closed if separation is unavailable.
9. Generate a subtle original procedural mood bed from detected emotions.
10. Mix voice, preserved non-dialogue audio and mood bed with conservative levels and final loudness mastering.
11. Export MP4 plus SRT and an audit manifest containing character, voice, emotion, timing, background and music metadata.

## Character handling

The current character assignment is transcript/context driven. If an upstream transcript already contains speaker IDs, those IDs should be preserved. Without speaker labels, the director model infers stable character groups from dialogue context. This is **not** acoustic speaker diarization and should not be represented as such.

Voice assignment is stable for a render. `voice=auto` allocates distinct voices from the configured voice pool where available. The voice names are model voice identifiers, not guaranteed biological gender labels.

## Timing guarantee

Each dubbed segment is constrained to the original segment's `[start, end]` window. Generated audio is speed-fitted and trimmed/padded as necessary. The manifest records `drift_ms`; production validation should reject segments outside the configured tolerance.

Exact timing is not the same as automatic lip-sync. Phoneme-level mouth animation requires a separate lip-sync/video stage. The current renderer keeps the original video frames unchanged.

## Audio preservation

When enabled, Demucs `--two-stems=vocals` is used to produce a non-vocal background stem. The final audio maps the generated dialogue instead of the original audio, so original dialogue is not intentionally reintroduced. Source separation can create artifacts and may also remove sung vocals from music; this is a known trade-off.

If Demucs is unavailable, background preservation fails safely rather than silently leaving the original speech underneath the dub.

## Smart Mood Music

`music_engine.py` generates an original procedural underscore locally from simple synthesized tones. It bundles no third-party recording and therefore does not depend on a third-party music Content-ID owner or attribution requirement. The engine supports neutral, happy, laughing, sad, crying, angry, scared, surprised, romantic, whispering, shouting and apologetic moods.

This is deliberately conservative background underscore, not a replacement for a full cinematic music library. For commercial production, user-supplied or explicitly licensed tracks can be added as a future provider with license metadata.

## Mastering

The final mix applies speech high/low-pass filtering, compression, limiting and a `-16 LUFS` loudness target before AAC export at 256 kbps. Background and mood music are kept substantially below the dialogue to protect intelligibility.

## Production safety

- Require `OPENAI_API_KEY` (or configured provider credentials) in the runtime environment.
- Do not hard-code API keys.
- Limit upload size and processing duration.
- Validate output paths before serving downloads.
- Keep original/licensed video and audio rights with the user.
- Store manifests for debugging and reproducibility.
- Do not promise that an AI dub is impossible to distinguish from human dubbing; quality depends on source audio, timing, translation, voices and whether a true lip-sync stage is available.

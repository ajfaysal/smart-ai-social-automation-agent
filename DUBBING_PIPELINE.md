# DubStudio AI — Production Dubbing Pipeline

## Pipeline

1. Extract source dialogue/transcript with timestamps.
2. Treat the source dialogue window as the master clock.
3. Build a director plan with stable character IDs and emotion labels.
4. Translate/adapt each line for natural spoken delivery while respecting its duration.
5. Generate character-consistent TTS with emotion-directed acting instructions.
6. Time-fit every generated clip with FFmpeg and verify drift.
7. Assemble the complete dialogue timeline, preserving silence between lines.
8. Export MP4 plus an audit manifest containing character, voice, emotion and timing data.

## Character handling

The current character assignment is transcript/context driven. If an upstream transcript already contains speaker IDs, those IDs should be preserved. Without speaker labels, the director model infers stable character groups from dialogue context. This is **not** acoustic speaker diarization and should not be represented as such.

Voice assignment is stable for a render. `voice=auto` allocates distinct voices from the configured voice pool where available. The voice names are model voice identifiers, not guaranteed biological gender labels.

## Timing guarantee

Each dubbed segment is constrained to the original segment's `[start, end]` window. Generated audio is speed-fitted and trimmed/padded as necessary. The manifest records `drift_ms`; production validation should reject segments outside the configured tolerance.

Exact timing is not the same as automatic lip-sync. Phoneme-level mouth animation requires a separate lip-sync/video stage.

## Audio preservation

The current core renderer replaces the source audio track with the generated dialogue timeline. Background music, ambience and sound effects are therefore not yet automatically separated and preserved. A future optional source-separation stage can extract non-dialogue stems and mix them beneath the dubbed dialogue.

## Production safety

- Require `OPENAI_API_KEY` (or the configured model provider credentials) in the runtime environment.
- Do not hard-code API keys.
- Limit upload size and processing duration.
- Validate output paths before serving downloads.
- Keep original/licensed video and audio rights with the user.
- Store manifests for debugging and reproducibility.

# Chinese drama: 30-character execution plan

A 30-character drama is handled as a speaker-identity problem first and a TTS problem second.

## Pipeline

`Chinese video → STT → speaker diarization → speaker embeddings → C01..C30 → reference voice bank → engine routing → translation → TTS → timing lock → lip-sync → QC`

### Voice bank

For each confirmed character:

- `character_id`: stable ID
- `speaker_id`: diarization ID
- `gender_hint`: female/male/unknown
- `reference_audio`: 10–30s clean speech clip when available
- `preferred_engine`: optional CosyVoice/Fish Speech/GPT-SoVITS/OpenVoice
- `fallback_engine`: another configured engine
- `target_language`: Bangla/English/Hindi
- `emotion_profile`: neutral/angry/sad/etc.

### Routing

No global `VOICE_POOL` is used for production character identity. Engine selection
is deterministic per character, and the same character keeps the same reference
voice across all scenes. If an engine fails, the character can move to another
configured engine while keeping the same reference sample.

### Failure rules

- uncertain diarization → mark character identity uncertain
- missing reference → use an explicitly documented synthetic/native fallback
- engine failure → fail over and record it in the manifest
- no valid voice path → failed-closed, never silently reuse one unrelated voice

This plan is designed specifically for Chinese drama dubbing, where many short
CJK dialogue turns make stable speaker identity more important than simply having
more TTS voices.

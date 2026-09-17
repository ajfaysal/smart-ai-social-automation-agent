# Multi-engine voice architecture for Chinese drama dubbing

V1 Chinese drama dubbing must not depend on one TTS model or one vendor.

## Character-count strategy

A drama can have 30+ speaking characters. The pipeline therefore treats a
character voice as a **stable identity**, not as a single global TTS voice.

1. STT + diarization produces speaker IDs such as `S01..S30`.
2. The director maps each speaker to a stable character ID (`C01..C30`) and
   records gender/profile/emotion hints.
3. A voice-bank layer stores a reference sample per character outside git.
4. The engine registry assigns characters across configured engines instead of
   forcing every character through one model.
5. Each engine receives the same character reference when it supports cloning.
6. The generated segment is timing-locked before final assembly.

## Open-source engine pool

The registry currently has adapters for:

- **CosyVoice** — multilingual/cross-lingual cloning; strong Chinese support.
- **Fish Speech** — multilingual, multi-speaker and short-reference cloning.
- **GPT-SoVITS** — few-shot/zero-shot cloning with strong Chinese support.
- **OpenVoice** — cross-lingual cloning and style controls.
- **Edge Bengali Neural** — deterministic fallback when an open-source runtime
  is unavailable.

The repository stores only adapter code and command templates. Model weights,
reference recordings, checkpoints and credentials stay in runtime storage.

## Runtime configuration

Each open-source engine is enabled only when its command environment variable
is configured:

- `COSYVOICE_TTS_COMMAND`
- `FISH_SPEECH_TTS_COMMAND`
- `GPT_SOVITS_TTS_COMMAND`
- `OPENVOICE_TTS_COMMAND`
- `BANGLA_REFERENCE_TTS_COMMAND` for a custom reference-audio adapter
- `BANGLA_REFERENCE_VOICE_DIR` for per-character references

Templates receive `{text}`, `{output}`, `{reference}`, and `{character}`.

## Important quality rule

The existing ten Bangla profiles are delivery variants over four native
Bengali voices. They are **not** treated as ten independent human timbres.
For a 30-character drama, the production path should therefore use cloned
reference voices or multiple open-source engines rather than merely changing
pitch/rate.

## Chinese-specific requirement

For Chinese dramas, speaker diarization/reference extraction is a separate
certification gate. The system must not silently assign arbitrary voices when
speaker identity is uncertain. A failed diarization or missing reference voice
must be visible in the provider manifest and must not be reported as a fully
certified character-voice result.

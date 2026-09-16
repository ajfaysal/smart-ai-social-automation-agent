# Chinese Drama Dubbing V1

V1 is intentionally focused on one source family and three dubbing targets:

- Source: Mandarin Chinese drama (`zh-CN` / `zh-TW` input variants)
- Target: Bangla (`bn`), English (`en`), Hindi (`hi`)

The existing broader language registry is intentionally preserved for future development. V1 routing does not delete or permanently disable those languages; it simply provides a tested launch contract for the Chinese-drama workflow.

## Audio contract

- Replace the original Chinese dialogue with the selected target-language dialogue.
- Remove the original dialogue/music bed from the final dubbed mix where configured by the audio-separation stage.
- Keep the original drama video unchanged.
- Keep non-dialogue scene audio only where the separation pipeline can isolate it reliably; do not claim perfect BGM/SFX separation without a validated provider result.
- Apply timing lock, character voice assignment, emotion-aware TTS, lip-sync, and final media QC.

## Target selection

The caller selects exactly one V1 target: Bangla, English, or Hindi. The selected target is passed through the canonical V1 routing contract so a target cannot silently fall back to another language.

Chinese-to-Chinese re-voice remains a technical test path only and is not a V1 dubbing certification target.

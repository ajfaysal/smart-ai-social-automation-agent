# AI Drama Dubbing & Social Automation Agent

Production-oriented, serverless tooling for AI-assisted Chinese drama dubbing and social automation.

## Drama dubbing pipeline

The production dubbing path is designed around an auditable, fail-closed workflow:

1. Public video URL download and FFprobe validation
2. OCR-guided on-screen Chinese text cleanup
3. Audio extraction and Demucs vocal separation
4. Speech-to-text with a canonical transcript/timeline
5. Speaker diarization and speaker-to-character identity mapping
6. Character-aware Bangla/English/Hindi voice routing
7. Emotion and timing-aware TTS
8. Replacement-dialogue-only audio mastering
9. Shot-aware Wav2Lip lip-sync
10. Final video assembly and QC
11. Strict certification with provider execution evidence

### V1 language scope

- Source: Chinese (Simplified or Traditional)
- Targets: Bangla, English, Hindi
- Same-language Chinese revoice is technical testing only and is not V1 certification.

### Audio policy

V1 removes the original dialogue and original music. Original SFX are not preserved by the replacement-dialogue-only mix. The generated provider manifest records this policy.

### Character voice routing

Character identity is separated from the TTS provider. A character can be assigned a deterministic voice profile and optional reference audio. Bangla has a native Bengali voice profile pool and optional reference-voice runtime hooks. Provider-specific reference cloning is only considered successful when the configured runtime actually supports it.

## Real GPU certification

The real certification path runs on a private Kaggle GPU kernel. Provider credentials and model URLs stay in Kaggle Secrets; they are never committed to Git or duplicated into GitHub workflow variables.

### Manual provider validation workflow

For isolated provider-level validation, use **Actions → Real Provider Validation → Run workflow**. Select a provisioned runner label and one provider profile (`demucs`, `mediapipe`, `wav2lip`, `whisper`, or `xtts-v2`). The runner must already contain the required provider runtime, model weights, and test media; heavyweight assets are never downloaded by default CI.

- Whisper requires runner-local audio plus the `WHISPER_LOCAL_COMMAND` secret and validates the large-v3 contract.
- XTTS-v2 requires runner-local text, reference audio, output path, and `XTTS_V2_TTS_COMMAND`; reference voice cloning is mandatory.
- Demucs, MediaPipe, and Wav2Lip require the corresponding runner-local media and configured provider runtime.
- Successful execution must produce a machine-readable `validation.json` containing `provider_execution`; malformed or missing reports fail closed.
- The workflow uploads `validation-artifacts/` and `provider-validation-work/` even when validation fails.

This workflow proves provider execution only when the selected provisioned runner actually runs the model-backed provider and produces validated artifacts. A dry-run or dispatch event is not certification.
### Dispatch

Use the GitHub Actions workflow: **Actions → Kaggle Real Certification Dispatch → Run workflow**.

Inputs: `video_url`, `language` (Bangla/English/Hindi), and `kernel_slug`.

The dispatch workflow does not require provider secrets in GitHub. It only validates the URL/language boundary and submits the Kaggle job.

### Retrieval and certification

Run `python kaggle_certification_operator.py <owner/kernel-slug> --timeout 3600 --poll 30` after the Kaggle kernel finishes.

A run is accepted only when `certification.json` contains `certified=true` and the bundle includes the final MP4, matching dubbing manifest, `speaker-identity.json`, `speaker-routing.json`, and `text-cleanup.json`. The operator also records a SHA-256 digest of the final MP4.

## Local development

Use the existing CI workflow for repository tests. Real provider credentials, model checkpoints, media, and reference audio remain runtime-only.

## Security

Never commit API keys, access tokens, Kaggle credentials, model checkpoints, private reference audio, source media, or generated media. If a credential is exposed, revoke or rotate it immediately.

## Social automation

The repository also retains the original serverless social-automation components for X/Twitter workflows. Those components are separate from the production dubbing certification path.
# Kaggle full real-provider pipeline

This runner executes the repository's canonical `dub_video()` pipeline inside a Kaggle GPU notebook. It is the production smoke/certification path, not a mocked CI test.

## Runtime flow

1. Public Google Drive video is downloaded and FFprobe-validated.
2. Repository dependencies are installed.
3. Wav2Lip is cloned into the ephemeral Kaggle runtime.
4. Wav2Lip checkpoint and S3FD detector URLs are read from Kaggle Secrets and downloaded only at runtime.
5. `OPENAI_API_KEY` is read from Kaggle Secrets.
6. `dub_video()` performs Whisper large-v3 transcription, character/emotion planning, Chinese translation/TTS, exact timing, Demucs separation, mastering, shot-aware Wav2Lip, and final QC/manifest generation.
7. Final MP4, SRT, manifest, and certification report are copied to `/kaggle/working/final-artifacts/`.

## Required Kaggle Secrets

Create these secrets in the Kaggle account that owns the kernel:

- `OPENAI_API_KEY` — translation/planning runtime
- `WHISPER_LOCAL_COMMAND` — provisioned Whisper large-v3 command wrapper
- `XTTS_V2_TTS_COMMAND` — provisioned XTTS-v2 command wrapper
- `REQUIRE_REFERENCE_VOICE_CLONING` — set to `true`
- `PYANNOTE_DIARIZATION_COMMAND` (or `THREE_D_SPEAKER_DIARIZATION_COMMAND` when that backend is selected)
- `WAV2LIP_CHECKPOINT_URL`
- `WAV2LIP_S3FD_URL`

The Whisper/XTTS commands are external runtime adapters; model weights, CUDA environments, and character reference recordings remain on the provisioned Kaggle runtime and are never committed to Git.

The model URLs are intentionally operator-managed because Wav2Lip's published project notes include licensing restrictions; the repository does not silently bundle or redistribute model weights.

## Certification rule

The notebook reports `certified` only when a final MP4 and manifest exist, all certified segment routes succeed with valid provider evidence, lip-sync is applied, and the canonical certification gate passes. A launched Kaggle job without these artifacts is not certification. Provider execution remains fail-closed: unavailable, failed, skipped, or invalid artifacts cannot be marked successful.

## Local notebook generation

```bash
python kaggle_full_pipeline.py \
  --video-url 'https://drive.google.com/file/d/FILE_ID/view?usp=sharing' \
  --language 'Chinese (Simplified)'
```

The generated notebook contains no Kaggle API credential. API launch remains handled by the existing `kaggle_gpu_orchestrator.py` path.

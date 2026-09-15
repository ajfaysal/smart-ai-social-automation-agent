# Kaggle full real-provider pipeline

This runner executes the repository's canonical `dub_video()` pipeline inside a Kaggle GPU notebook. It is the production smoke/certification path, not a mocked CI test.

## Runtime flow

1. Public Google Drive video is downloaded and FFprobe-validated.
2. Repository dependencies are installed.
3. Wav2Lip is cloned into the ephemeral Kaggle runtime.
4. Wav2Lip checkpoint and S3FD detector URLs are read from Kaggle Secrets and downloaded only at runtime.
5. `OPENAI_API_KEY` is read from Kaggle Secrets.
6. `dub_video()` performs transcription, character/emotion planning, Chinese translation/TTS, exact timing, Demucs separation, mood music, mastering, shot-aware Wav2Lip, and final QC/manifest generation.
7. Final MP4, SRT, manifest, and certification report are copied to `/kaggle/working/final-artifacts/`.

## Required Kaggle Secrets

Create these secrets in the Kaggle account that owns the kernel:

- `OPENAI_API_KEY`
- `WAV2LIP_CHECKPOINT_URL`
- `WAV2LIP_S3FD_URL`

The model URLs are intentionally operator-managed because Wav2Lip's published project notes include licensing restrictions; the repository does not silently bundle or redistribute model weights.

## Certification rule

The notebook reports `certified` only when a final MP4 and manifest exist and the canonical pipeline reports lip-sync as applied. Provider execution remains fail-closed: unavailable, failed, skipped, or invalid artifacts cannot be marked successful.

## Local notebook generation

```bash
python kaggle_full_pipeline.py \
  --video-url 'https://drive.google.com/file/d/FILE_ID/view?usp=sharing' \
  --language 'Chinese (Simplified)'
```

The generated notebook contains no Kaggle API credential. API launch remains handled by the existing `kaggle_gpu_orchestrator.py` path.

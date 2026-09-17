# Real Chinese → Bangla GPU Run

This is the operator handoff for the first real V1 dubbing run. The repository does not claim a certification until the generated MP4, manifest, subtitle file, lip-sync artifact, and final QC report are actually produced.

## V1 contract

- Source: Chinese (Simplified) or Chinese (Traditional)
- Target: Bangla, English, or Hindi
- First real certification target: **Chinese → Bangla**
- Original Chinese dialogue: removed
- Original music: removed
- Original background bed/SFX: not preserved in V1 because the current two-stem Demucs path cannot reliably isolate BGM from SFX
- Video visuals: retained as the source video, subject to the optional text/sticker/watermark cleanup stage

## Kaggle setup

Create a private Kaggle notebook from the generated notebook produced by `kaggle_gpu_orchestrator.py` and enable:

- GPU
- Internet

Add these Kaggle Secrets:

- `OPENAI_API_KEY`
- `WAV2LIP_CHECKPOINT_URL`
- `WAV2LIP_S3FD_URL`

The values are read at runtime only. Do not commit credentials, model weights, model URLs, or source media to GitHub.

## Generate the real-run notebook

```bash
python kaggle_gpu_orchestrator.py \
  --video-url 'PUBLIC_VIDEO_URL' \
  --language Bangla \
  --kernel-slug drama-dubbing-chinese-bangla \
  --dry-run > kaggle_full_pipeline.json
```

For an authenticated Kaggle push from an environment that has the Kaggle CLI configured:

```bash
python kaggle_gpu_orchestrator.py \
  --video-url 'PUBLIC_VIDEO_URL' \
  --language Bangla \
  --kernel-slug drama-dubbing-chinese-bangla
```

The launcher reads `KAGGLE_API_TOKEN` or `KAGGLE_API_KEY` from the runtime environment only.

## Expected artifacts

The notebook writes to `/kaggle/working/final-artifacts/`:

- final dubbed MP4
- dubbing manifest JSON
- SRT subtitle file
- `cloud-provider-certification.json`

A run is **certified** only when the final MP4 and manifest exist and the Wav2Lip result reports `applied=true`. Missing/failed provider artifacts must produce `failed_closed`, not a false certification.

## First run

Use the real public video fixture already selected for the project and target `Bangla`. Do not substitute the synthetic fixture for certification. The synthetic fixture is only for deterministic local tests.

If the Kaggle kernel cannot start or a runtime secret is missing, treat the run as blocked rather than claiming a successful dubbing result.

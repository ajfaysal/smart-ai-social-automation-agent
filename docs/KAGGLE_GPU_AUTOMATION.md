# Automatic Kaggle GPU dubbing

The Kaggle API is the remote execution trigger, not just a credential store.

## Flow

1. `kaggle_gpu_orchestrator.py` reads `KAGGLE_API_TOKEN` or `KAGGLE_API_KEY` from the runtime environment.
2. It generates a temporary Kaggle notebook and kernel metadata with GPU + internet enabled.
3. Kaggle provisions the remote GPU runtime.
4. The runtime clones the selected repository revision.
5. The runtime downloads the public Google Drive video and validates it with FFprobe.
6. Demucs runs in the remote runtime and is audited only after its artifact validates.
7. In `full` mode, MediaPipe and Wav2Lip execute when their runtime inputs/checkpoint are present; otherwise the run records that the provider was not executed instead of claiming success.
8. Provider audit/QC remains fail-closed.

## Launch

```bash
export KAGGLE_API_TOKEN='YOUR_RUNTIME_SECRET'
python kaggle_gpu_orchestrator.py \
  --video-url 'https://drive.google.com/file/d/FILE_ID/view?usp=sharing' \
  --profile full
```

No credential, video, cookie, or model checkpoint is written to Git.

## Wav2Lip runtime inputs

Provide the model/checkpoint and input assets in the Kaggle runtime according to the existing Wav2Lip provider configuration. The orchestrator intentionally does not download an unverified third-party checkpoint or silently mark Wav2Lip as successful.

## Certification rule

A remote GPU job being launched is **not** itself provider certification. Certification requires real provider execution plus validated output artifacts and a matching audit manifest.

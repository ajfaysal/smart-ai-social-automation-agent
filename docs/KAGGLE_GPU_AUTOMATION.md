# Kaggle GPU automation

`kaggle_gpu_orchestrator.py` is the API-driven launch layer for real-provider smoke execution.

## What it does

1. Reads the Kaggle credential from `KAGGLE_API_TOKEN` or `KAGGLE_API_KEY` at runtime.
2. Generates a temporary Jupyter notebook from the repository revision.
3. Creates Kaggle kernel metadata with GPU and internet enabled.
4. Pushes the kernel through the Kaggle CLI, causing Kaggle to provision the GPU runtime.
5. The kernel clones this repository, installs runtime dependencies, downloads the public Drive fixture, and FFprobe-validates it.

Credentials, runtime media, and model checkpoints are never committed to Git.

## Launch

```bash
export KAGGLE_API_TOKEN='YOUR_RUNTIME_SECRET'
python kaggle_gpu_orchestrator.py \
  --video-url 'https://drive.google.com/file/d/FILE_ID/view?usp=sharing' \
  --profile full
```

For a local contract check without contacting Kaggle:

```bash
python kaggle_gpu_orchestrator.py \
  --video-url 'https://drive.google.com/file/d/FILE_ID/view?usp=sharing' \
  --dry-run
```

## Provider execution

The Kaggle kernel is the GPU execution layer; provider certification still follows the repository's fail-closed audit contract. Demucs, MediaPipe, and Wav2Lip must produce validated artifacts before they can be recorded as `SUCCEEDED`/`applied=true`.

Wav2Lip model checkpoints remain operator-managed runtime assets. They are not bundled into Git and must be installed or supplied in the Kaggle runtime before Wav2Lip certification.

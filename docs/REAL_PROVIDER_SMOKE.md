# Real Provider Smoke Validation

Issue #21 defines the operator-side certification pass for real Demucs, MediaPipe and Wav2Lip execution. Heavy model weights, credentials and copyrighted media are intentionally kept outside the repository.

## Prerequisites

- Python 3.11+
- FFmpeg + FFprobe
- A small operator-owned or properly licensed media fixture
- Demucs installed for source separation
- MediaPipe + OpenCV for landmark analysis
- Wav2Lip runtime, checkpoint and its dependencies for lip-sync

Standard PR CI does **not** install these heavy runtimes.

## Independent validation

### Demucs

```bash
python real_provider_runner.py demucs \
  --audio /path/to/source.wav \
  --work provider-validation-work
```

Success requires a real `no_vocals.wav` artifact produced by Demucs and accepted by the provider audit validator.

### MediaPipe

For a single frame/image:

```bash
MOUTH_LANDMARK_PROVIDER=mediapipe \
python real_provider_runner.py mediapipe \
  --image /path/to/face-frame.jpg
```

For real-video certification, extract a representative frame set with FFmpeg or an operator-owned preprocessing step, then validate the eligible frames. A single successful landmark call must not be interpreted as whole-video lip-sync certification.

### Wav2Lip

Configure the provider command and checkpoint according to `lip_sync_provider.py`, then run:

```bash
LIPSYNC_PROVIDER=wav2lip \
python real_provider_runner.py wav2lip \
  --video /path/to/source.mp4 \
  --audio /path/to/dubbed.wav \
  --output provider-validation-work/wav2lip-output.mp4
```

Success requires a validated output video artifact. The provider must be configured with a real model checkpoint; configuration alone never counts as success.

## Manual GitHub Actions validation

Use **Actions → Real Provider Validation → Run workflow**. The default `dry-run` profile only executes deterministic contract tests. Provider profiles require paths that already exist on the selected runner; the workflow does not upload arbitrary media or model weights into the repository.

For hosted runners, remember that a runner-local path must actually exist on that runner. For GPU certification, use a self-hosted GPU runner or an equivalent controlled execution environment and reproduce the same commands there.

## GPU guidance

- Verify the NVIDIA driver and CUDA runtime required by the installed PyTorch/Wav2Lip stack.
- Confirm the runtime sees the GPU before starting inference.
- Keep model checkpoints outside Git and outside workflow logs.
- Record provider/runtime versions in the certification evidence.
- If a prerequisite is missing, record `UNAVAILABLE`, `CONFIGURED`, `FAILED`, or `SKIPPED` as appropriate; never convert it to success.

## Certification evidence

Keep the following as ephemeral workflow artifacts or operator notes:

1. provider command and runtime versions;
2. provider execution manifest/QC JSON;
3. validated artifact metadata (size, media streams, duration where applicable);
4. failure/fallback reason when a provider cannot run;
5. integrated dubbing QC result when all required providers are available.

Do not commit model weights, secrets, or copyrighted source media.

# Real Provider Validation

This profile verifies provider execution without treating configuration as success.

## States

Providers use the shared execution states from `provider_reliability.py`.
A provider is `SUCCEEDED` and `applied: true` only when the expected output artifact exists, is a file, meets the minimum size, and has the expected suffix.

## Default CI

Normal CI remains credential-free and does not download large model weights. The manual workflow runs the deterministic artifact/reliability contract tests and records the selected profile.

## Real execution

Real model-backed execution is intentionally opt-in. Configure the provider on a suitable runner or local environment, execute the provider command, then validate its concrete output with `ArtifactExpectation` before marking the provider successful.

- Demucs: expected separated background/vocal artifact, typically WAV.
- MediaPipe: expected landmark output from the configured landmark provider.
- Wav2Lip: expected rendered video from the configured Wav2Lip command and checkpoint.

A missing, malformed, too-small, or otherwise invalid artifact must remain `FAILED`; it must never be reported as applied.

The GitHub Actions workflow supports an explicit `runner_label` input. Keep `ubuntu-latest` for the credential-free contract profile; for real provider execution, select a self-hosted/provisioned runner label that already contains the required dependencies, model weights, hardware, and runner-local media. The workflow never downloads heavyweight models or treats runner selection as provider success.


## Operator checklist

The repository never supplies provider credentials, model weights, source media, or reference audio. Provision them only on the selected validation runner.

### Demucs

1. Provision Python/audio dependencies and a real Demucs installation on the runner.
2. Provide an input audio file through the workflow's `media_path` input or directly to `real_provider_runner.py`.
3. Run:

```bash
python real_provider_runner.py demucs --audio /path/to/input.wav --work provider-validation-work
```

Expected result: the JSON report contains a provider execution with `state=succeeded`, `applied=true`, and an existing validated separation artifact. A missing or invalid artifact is a failed validation.

### MediaPipe

1. Provision OpenCV and the configured MediaPipe landmark runtime on the runner.
2. Set `MOUTH_LANDMARK_PROVIDER=mediapipe`.
3. Provide a representative frame and run:

```bash
MOUTH_LANDMARK_PROVIDER=mediapipe python real_provider_runner.py mediapipe --image /path/to/frame.jpg
```

Expected result: the report contains face/landmark evidence and a successful provider execution. No detected mouth must fail the validation rather than produce an applied result.

### Wav2Lip

1. Provision the Wav2Lip command wrapper and checkpoint outside Git.
2. Set `LIPSYNC_PROVIDER=wav2lip`, `WAV2LIP_COMMAND`, and `WAV2LIP_MODEL_PATH` on the runner.
3. Provide video and replacement dialogue audio:

```bash
LIPSYNC_PROVIDER=wav2lip WAV2LIP_MODEL_PATH=/secure/models/wav2lip.pth \\
python real_provider_runner.py wav2lip --video /path/to/input.mp4 \\
  --audio /path/to/dialogue.wav --output provider-validation-work/wav2lip-output.mp4
```

Expected result: the rendered MP4 exists, passes the media validation, and the provider audit reports `succeeded` with `applied=true`. A command failure or invalid output remains failed.

## GitHub Actions profile

The **Real Provider Validation** workflow is an operator-triggered contract runner. It does not install heavyweight model packages or expose provider credentials. The `dry-run` option is safe for ordinary CI-style verification on `ubuntu-latest`; provider-specific options should use a self-hosted/provisioned `runner_label` whose filesystem contains the requested media and whose environment contains the command, model, and hardware dependencies. Runner selection is recorded in the validation artifact.

Validation artifacts include the JSON report and the provider work/output directory. Missing artifacts cause the upload step to fail instead of being silently ignored.

## Certification boundary

This validation profile is not V1 Chinese→Bangla/English/Hindi certification by itself. Certification additionally requires the real GPU pipeline, successful speaker identity/routing, applied lip-sync where required, final QC, the complete execution manifest, and the certification bundle described in the repository's Kaggle certification documentation.

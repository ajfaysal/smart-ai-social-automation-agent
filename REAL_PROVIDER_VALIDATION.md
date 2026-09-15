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

The current GitHub Actions workflow is a safe contract-validation profile. It does not pretend that GitHub-hosted CI has executed heavyweight model inference. Actual model-backed validation should be run only when the required dependencies, model weights, and hardware are deliberately provisioned.

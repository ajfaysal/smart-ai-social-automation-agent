# Real provider execution audit

The production dubbing pipeline now has an auditable runtime registry for optional
model-backed providers.

## States

- `unavailable`: provider is not installed/configured.
- `configured`: provider is ready but has not run.
- `attempted`: execution started but no successful artifact has been accepted.
- `succeeded`: the expected output artifact was produced and validated.
- `failed`: execution or artifact validation failed.
- `skipped`: the pipeline deliberately did not run the provider.

Only `succeeded` executions may have `applied: true`.

## Wav2Lip

Set `LIPSYNC_PROVIDER=wav2lip`, `WAV2LIP_COMMAND`, and
`WAV2LIP_MODEL_PATH`. The provider invokes the configured command and refuses to
report success unless an MP4 artifact exists and passes the minimum artifact
validation gate.

## MediaPipe

Set `MOUTH_LANDMARK_PROVIDER=mediapipe`. Real landmark detection is attempted
only when MediaPipe is installed. A visible mouth/landmark result is recorded as
successful; missing faces and detection errors are recorded as failures.

## Demucs

The existing production separation path still requires an installed `demucs`
command and refuses to continue when the expected `no_vocals.wav` stem is absent.
The runtime registry provides the common artifact-validation contract; direct
Demucs registry wiring should be completed before treating a full pipeline run
as provider-audited end to end.

## Default CI

No model weights or external provider credentials are downloaded by default.
The deterministic runtime tests exercise missing, invalid, configured, and
successful artifact states.

The shot lip-sync manifest persists the runtime provider execution snapshot so a
real Wav2Lip/MediaPipe execution can be audited after a manual model-backed run.

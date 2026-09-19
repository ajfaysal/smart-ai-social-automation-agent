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
  --language Bangla
```

No credential, video, cookie, or model checkpoint is written to Git.

## Wav2Lip runtime inputs

Provide the model/checkpoint and input assets in the Kaggle runtime according to the existing Wav2Lip provider configuration. The orchestrator intentionally does not download an unverified third-party checkpoint or silently mark Wav2Lip as successful.

## Certification rule

A remote GPU job being launched is **not** itself provider certification. Certification requires real provider execution plus validated output artifacts and a matching audit manifest.

## V1 Whisper + XTTS runtime contract

For the V1 Chinese → Bangla/English/Hindi certification path, the provisioned Kaggle runtime must expose these Secrets:

- `WHISPER_LOCAL_COMMAND` — command wrapper for Whisper large-v3; it must accept `{audio}`, `{output}`, and `{model}` and write verbose JSON containing timestamped `segments`.
- `XTTS_V2_TTS_COMMAND` — XTTS-v2 wrapper accepting `{text}`, `{output}`, `{reference}`, `{character}`, `{acting_directive}`, and `{language}`.
- `REQUIRE_REFERENCE_VOICE_CLONING=true`.
- The selected diarization command, Wav2Lip checkpoint URLs, and `OPENAI_API_KEY`.

The orchestrator preflight fails before dispatch when the required Whisper/XTTS commands are absent. Dispatch-only mode intentionally skips provider runtime requirements so notebook generation can be tested without secrets.

A successful dispatch is only an execution trigger. The final certification bundle must be inspected before declaring the run certified.

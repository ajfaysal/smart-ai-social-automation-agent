# Colab real-provider runner

This runner is intentionally operator-driven. It downloads a public video fixture at runtime, validates it with FFprobe, and then invokes the repository's real-provider profiles. No video, model weights, cookies, or secrets are committed.

## 1. Start Colab

Use a GPU runtime when validating Wav2Lip. CPU is acceptable for lightweight download/media checks and may be acceptable for MediaPipe/Demucs depending on fixture size.

## 2. Clone and install

```bash
!git clone https://github.com/ajfaysal/smart-ai-social-automation-agent.git
%cd smart-ai-social-automation-agent
!pip install -r requirements-cloud-runner.txt
!pip install -r requirements.txt
```

Install the real provider prerequisites required by the selected profile. For Wav2Lip, install the operator-managed Wav2Lip environment and model checkpoint; do not commit the checkpoint.

## 3. Download and validate the public Drive video

```python
VIDEO_URL = "PASTE_PUBLIC_GOOGLE_DRIVE_SHARE_URL_HERE"
```

```bash
!python cloud_video_input.py "$VIDEO_URL" --output validation-input/source.mp4
```

The command must print `validated: True`. If Drive returns an HTML page, fix the sharing permission or use a direct media URL. Never add cookies or access tokens to the repository.

## 4. Run a provider smoke profile

The repository's `real_provider_runner.py` supports provider-specific execution. Use the smallest operator-owned fixture first.

Demucs:

```bash
!python real_provider_runner.py demucs --input validation-input/source.mp4 --output validation-artifacts/demucs
```

MediaPipe:

```bash
!python real_provider_runner.py mediapipe --input validation-input/source.mp4 --output validation-artifacts/mediapipe
```

Wav2Lip:

```bash
!python real_provider_runner.py wav2lip --video validation-input/source.mp4 --audio validation-input/dubbed.wav --output validation-artifacts/wav2lip.mp4
```

Use the exact `--help` output from the checked-out revision if an argument differs; the provider runner is the source of truth.

## 5. Evidence

Keep the generated `validation.json`, provider execution state, FFprobe metadata, and final media artifact in the Colab session or copy them to operator-controlled storage. A provider is certified only when its execution state is `SUCCEEDED`, `applied=true`, and its output artifact passes validation.

## Security

Do not paste API keys, Kaggle tokens, cookies, or private Drive URLs into notebook cells that will be shared. Use Colab Secrets for credentials. Public media URLs are still treated as runtime input only.

# Cloud video input

The real-provider smoke runner can use an operator-owned public video URL instead of requiring a ChatGPT upload.

## Google Drive

Set the file to **Anyone with the link → Viewer**, then pass the normal share URL:

```bash
python cloud_video_input.py 'https://drive.google.com/file/d/FILE_ID/view?usp=sharing' --output validation-input/source.mp4
```

The downloader extracts the Drive file ID and requests the binary download endpoint. It fails closed if Drive returns an HTML page instead of media bytes.

## Direct URLs

Ordinary public HTTP(S) video URLs are also supported:

```bash
python cloud_video_input.py 'https://example.com/source.mp4' --output validation-input/source.mp4
```

## Security

Do not put API keys, Kaggle tokens, cookies, or private download URLs in the repository. Cloud credentials belong in Kaggle/Colab/GitHub Secrets. The downloaded fixture is runtime-only and is not committed.

After download, FFprobe requires both a video and audio stream and a duration of at least 0.1 seconds. Only a validated fixture should be passed to the real-provider profiles.

# Real Lip-sync Setup

DubStudio now has a provider boundary for real video lip-sync. It is disabled by default so the renderer never falsely reports mouth animation.

## Enable Wav2Lip adapter

Set:

```text
LIPSYNC_PROVIDER=wav2lip
WAV2LIP_COMMAND=wav2lip
WAV2LIP_MODEL_PATH=/absolute/path/to/model.pth
```

The configured command must accept:

```text
wav2lip --video INPUT --audio AUDIO --checkpoint MODEL --outfile OUTPUT
```

The model weights are intentionally not committed to Git. Install and validate the selected Wav2Lip runtime and model separately, then enable the provider.

## API

`POST /api/dub` accepts `lip_sync=true`.

If the provider is unavailable, the job returns the normal timing-locked dub with `lip_sync_applied=false` rather than pretending the mouths were synchronized.

`GET /api/health` reports the configured provider and whether it is available.

Every render writes a lip-sync preparation JSON and includes provider/QC status in the final manifest.

## Important quality note

Real lip-sync quality depends on visible faces, camera angle, occlusion, cuts, source resolution and the selected model. A provider adapter is therefore kept separate from translation, TTS, audio preservation and mastering.

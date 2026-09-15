# Real Media Validation

The production dubbing pipeline now has an opt-in real-media QC profile.

## Local

Set `RUN_REAL_MEDIA_VALIDATION=1` and run:

```bash
python -m pytest -q tests/test_real_media_validation.py
```

The test generates a small real MP4 with FFmpeg and verifies:

- video and audio streams are present
- final duration is within the existing 80 ms QC tolerance
- dialogue timing drift is within tolerance
- shot boundaries are contiguous and cover the full media duration
- final QC reports a passing result

## CI

The default Drama Dubbing CI remains deterministic and does not require media fixtures, credentials, Demucs weights, or Wav2Lip weights.

A separate GitHub Actions workflow, **Real Media Validation**, is available through manual `workflow_dispatch`. It runs the same real-media test on an Ubuntu runner with FFmpeg available.

This validates the media/QC boundary only. It does not prove subjective translation quality, voice identity, Demucs separation quality, or actual Wav2Lip mouth animation quality.

# Real Media Validation Notes

The opt-in validation profile generates a small real MP4 with FFmpeg and sends it through the existing shot-continuity and final stream/duration/timing QC boundaries.

Default CI does not require FFmpeg media generation, API credentials, Demucs weights, or Wav2Lip weights. Use the manual Real Media Validation workflow for the media-level check.

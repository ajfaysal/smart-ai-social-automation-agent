# Lip-sync face validation

The dubbing pipeline now has an explicit face-validation boundary before real
mouth animation. Scene detection alone is not treated as face detection.

## Current behavior

- If no real face detector is configured, shots are marked `not_configured`.
- The pipeline must not claim lip-sync was applied for those shots.
- `ffmpeg` scene analysis only supplies shot boundaries; it cannot provide
  reliable face landmarks or mouth visibility.

## Detector contract

A future detector should emit, per shot:

- `face_count`
- `suitable`
- `confidence`
- `status`
- optional primary-face bounding box/landmarks

A shot should be eligible only when a sufficiently confident speaking face is
visible. Side profiles, heavy occlusion, very small faces, cuts, and shots with
no visible mouth should be rejected or routed to an appropriate provider mode.

This boundary keeps the system honest: timing-locked dubbing remains available
when face animation cannot be safely performed.

# Shot-aware lip-sync pipeline

`shot_lipsync.py` provides the production orchestration boundary for visual
lip-sync:

1. Cut source video into shot clips.
2. Run face tracking eligibility for each shot.
3. Run the configured lip-sync provider only on eligible shots.
4. Keep the original shot when eligibility or provider execution fails.
5. Reassemble all shots in source order.
6. Emit an auditable `shot_lipsync_manifest.json`.

The provider receives the exact shot audio window, so timing remains local to
the shot. The final application should still run global duration/stream QC.

## Safety behavior

A provider failure never becomes a success record. Shots without a suitable
face remain visually untouched. This means a video can contain a mixture of
lip-synced and untouched shots without silently corrupting non-speaking scenes.

## Current limitation

The existing Wav2Lip adapter is provider-level and model-dependent. This module
creates the correct shot-level orchestration boundary, but a real Wav2Lip model
and executable must be installed/configured before any visual animation occurs.

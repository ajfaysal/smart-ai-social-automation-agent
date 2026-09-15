# Landmark Lip-Sync Backend

The dubbing pipeline now has a separate facial-landmark provider boundary.

## Default

`LANDMARK_PROVIDER=disabled`

No landmark processing is claimed or performed by default.

## MediaPipe backend

Install the optional dependency in the runtime environment:

```bash
pip install mediapipe
```

Then configure:

```bash
LANDMARK_PROVIDER=mediapipe
```

The backend detects facial landmarks and evaluates the mouth region before a
shot can be considered suitable for a landmark-aware lip-sync stage.

## Important

This provider boundary is intentionally separate from the actual lip-sync
renderer. Landmark detection alone does **not** animate a mouth. A real video
lip-sync provider (such as the configured Wav2Lip adapter) is still required.

The current MediaPipe adapter is a conservative integration layer. For a
commercial production pipeline, validate the exact MediaPipe version and
landmark semantics in the deployment environment, then add temporal tracking,
face identity tracking, occlusion handling and calibrated confidence thresholds.

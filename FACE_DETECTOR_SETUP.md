# Face detector setup

The lip-sync pipeline now supports an optional local OpenCV Haar-cascade face
validation runtime.

## Install

Install the optional dependency with:

```bash
pip install opencv-python-headless
```

The application remains usable without it. In that case face validation is
reported as unavailable and real lip-sync must not be claimed as applied.

## What it does

The detector samples representative frames and looks for sufficiently large
frontal-face candidates. It is a conservative eligibility check, not a
full facial-landmark tracker and not a lip-sync engine.

For production-quality mouth animation, a landmark/face-tracking model should
replace or augment this detector before enabling automatic per-shot animation.

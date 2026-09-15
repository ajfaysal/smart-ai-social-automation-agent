# Shot-level lip-sync routing

The dubbing pipeline now has a conservative shot-level eligibility layer:

`video -> shot detection -> face detection -> sampled face track -> eligibility -> lip-sync provider -> QC`

A shot is eligible only when at least two samples succeed and at least 60%
of sampled frames retain a suitable, reasonably stable primary face.

Rejected shots must retain their original video frames. They can still receive
the timing-locked dubbed audio. This prevents the system from claiming visual
lip-sync where the face is absent, too small, occluded, or unstable.

## Current detector

`opencv-haar-sampled-center-track` is intentionally lightweight and conservative.
It is not a facial-landmark model and cannot prove phoneme-level mouth alignment.
For premium production, replace/augment it with a landmark-capable tracker and
keep the same manifest contract.

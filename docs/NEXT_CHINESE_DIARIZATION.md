# Next gate: Chinese speaker diarization + voice-bank extraction

Before claiming 30-character Chinese dubbing quality, the system needs a real speaker identity layer.

Target: detect stable speaker IDs across scenes, extract clean reference speech, then route each character to a stable voice engine/reference.

Candidate runtime families: pyannote/speaker-diarization, SpeechBrain speaker embeddings, and other credential-free or explicitly configured open-source diarization backends. The implementation should keep the backend pluggable and fail closed when identity confidence is insufficient.

Acceptance:
- repeated lines from the same source speaker keep the same speaker ID
- different speakers get different IDs when separable
- 10–30 second clean reference clips can be produced without committing media
- character voice catalog records engine + reference + confidence
- 30-character synthetic test proves no accidental single-voice collapse

"""Timestamp-based bridge from diarization turns to transcript segments."""
from __future__ import annotations

from speaker_identity import SpeakerTurn, normalize_speaker_id


def assign_speakers_to_segments(segments, turns, minimum_overlap=0.25):
    """Return transcript segments with deterministic speaker IDs when overlap is sufficient."""
    normalized = []
    for turn in turns:
        normalized.append((normalize_speaker_id(turn.speaker_id), float(turn.start), float(turn.end), float(turn.confidence)))
    out = []
    for index, segment in enumerate(segments):
        start, end, text = segment[:3]
        best = None
        best_overlap = 0.0
        for sid, ts, te, confidence in normalized:
            overlap = max(0.0, min(float(end), te) - max(float(start), ts))
            if overlap > best_overlap:
                best_overlap = overlap
                best = (sid, confidence)
        item = {"index": index, "start": float(start), "end": float(end), "text": str(text)}
        if best and best_overlap / max(0.001, float(end) - float(start)) >= minimum_overlap:
            item["speaker_id"] = best[0]
            item["speaker_confidence"] = best[1]
        out.append(item)
    return out

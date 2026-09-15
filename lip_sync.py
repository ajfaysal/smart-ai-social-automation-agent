"""Lip-sync preparation and QC layer for DubStudio AI.

This module deliberately does not fake phoneme-level mouth animation. It prepares
an auditable timing plan from the dubbed segments and exposes a provider-neutral
hook for a real video lip-sync engine.
"""
from pathlib import Path
import json


VISeme_BUCKETS = {
    "a": "open",
    "e": "wide",
    "i": "smile",
    "o": "round",
    "u": "pucker",
    "m": "closed",
    "b": "closed",
    "p": "closed",
    "f": "teeth",
    "v": "teeth",
    "s": "narrow",
    "sh": "narrow",
    "t": "narrow",
    "k": "open",
    "g": "open",
    "n": "closed",
    "l": "wide",
    "r": "round",
}


def normalize_text(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def estimate_viseme_plan(text: str, start: float, end: float):
    """Create a coarse provider-neutral mouth-shape plan.

    It is an alignment aid, not a claim of frame-accurate facial animation.
    """
    text = normalize_text(text)
    duration = max(0.01, end - start)
    chars = [c for c in text if c.isalpha()]
    if not chars:
        return []
    step = duration / len(chars)
    plan = []
    for i, char in enumerate(chars):
        bucket = VISeme_BUCKETS.get(char, "neutral")
        plan.append({"start": round(start + i * step, 4), "end": round(start + (i + 1) * step, 4), "shape": bucket})
    return plan


def build_lip_sync_plan(manifest, output_path: Path):
    plan = []
    for item in manifest:
        plan.append({
            "index": item["index"],
            "character": item["character"],
            "start": item["start"],
            "end": item["end"],
            "translation": item["translation"],
            "visemes": estimate_viseme_plan(item["translation"], item["start"], item["end"]),
        })
    output_path.write_text(json.dumps({
        "version": "1.0",
        "mode": "provider-neutral-preparation",
        "frame_animation": False,
        "segments": plan,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path

"""Manual runner for real provider validation.

This entry point is intentionally operator-driven: media and model weights stay
outside the repository. Standard CI must continue using deterministic mocks.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from demucs_provider import separate
from landmark_provider import get_landmark_provider
from lip_sync_provider import get_lip_sync_provider
from drama_dubbing import transcribe
from tts_provider import synthesize_reference_tts
from tts_artifact_qc import validate_tts_artifact
from provider_media_validation import validate_video_audio
from provider_runtime import reset_provider_executions, snapshot, validate_provider_snapshot


def run_demucs(audio: Path, work: Path) -> dict:
    reset_provider_executions()
    output = separate(audio, work)
    return {"output": str(output), "provider_execution": snapshot()}


def run_mediapipe(image: Path) -> dict:
    reset_provider_executions()
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required for MediaPipe validation.") from exc
    frame = cv2.imread(str(image))
    if frame is None:
        raise RuntimeError(f"Unable to read image: {image}")
    result = get_landmark_provider().detect(frame)
    audit = snapshot()
    if not result.mouth_visible:
        raise RuntimeError(result.reason)
    return {"face_count": result.face_count, "mouth_visible": result.mouth_visible,
            "confidence": result.confidence, "provider_execution": audit}


def run_whisper(audio: Path, work: Path) -> dict:
    reset_provider_executions()
    os.environ.setdefault("DUBBING_STT_PROVIDER", "local-whisper")
    result = transcribe(audio)
    segments = result.get("segments") if isinstance(result, dict) else None
    if not isinstance(segments, list) or not segments:
        raise RuntimeError("Whisper validation requires a non-empty segments array.")
    target = work / "whisper-transcript.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if target.stat().st_size < 16:
        raise RuntimeError("Whisper validation did not produce a valid transcript artifact.")
    return {"output": str(target), "segments": len(segments), "provider_execution": snapshot()}


def run_xtts(text: Path, reference: Path, output: Path, language: str) -> dict:
    reset_provider_executions()
    os.environ.setdefault("REQUIRE_REFERENCE_VOICE_CLONING", "true")
    text_value = text.read_text(encoding="utf-8").strip()
    if not text_value:
        raise RuntimeError("XTTS-v2 validation text must not be empty.")
    engine = synthesize_reference_tts(text_value, output, character_id=reference.stem, target_language=language, reference_audio=str(reference), preferred_engine="xtts-v2")
    qc = validate_tts_artifact(output)
    return {"output": str(output), "engine": engine, "tts_validation": qc, "provider_execution": snapshot()}


def run_wav2lip(video: Path, audio: Path, output: Path) -> dict:
    reset_provider_executions()
    provider = get_lip_sync_provider()
    result = provider.apply(video, audio, output)
    audit = snapshot()
    if not result.applied:
        raise RuntimeError(result.reason)
    media = validate_video_audio(result.output_path)
    return {"output": str(result.output_path), "media_validation": media,
            "provider_execution": audit}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one real provider validation profile.")
    parser.add_argument("provider", choices=("demucs", "mediapipe", "wav2lip", "whisper", "xtts-v2"))
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--text", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--language", default="bn")
    parser.add_argument("--work", type=Path, default=Path("provider-validation-work"))
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)

    if args.provider == "whisper":
        if not args.audio:
            parser.error("whisper requires --audio")
        result = run_whisper(args.audio, args.work)
    elif args.provider == "xtts-v2":
        if not args.text or not args.reference or not args.output:
            parser.error("xtts-v2 requires --text, --reference and --output")
        result = run_xtts(args.text, args.reference, args.output, args.language)
    elif args.provider == "demucs":
        if not args.audio:
            parser.error("demucs requires --audio")
        result = run_demucs(args.audio, args.work)
    elif args.provider == "mediapipe":
        if not args.image:
            parser.error("mediapipe requires --image")
        os.environ.setdefault("MOUTH_LANDMARK_PROVIDER", "mediapipe")
        result = run_mediapipe(args.image)
    else:
        if not args.video or not args.audio or not args.output:
            parser.error("wav2lip requires --video, --audio and --output")
        os.environ.setdefault("LIPSYNC_PROVIDER", "wav2lip")
        result = run_wav2lip(args.video, args.audio, args.output)

    valid, reason = validate_provider_snapshot(result["provider_execution"])
    if not valid:
        raise RuntimeError(f"Provider audit validation failed: {reason}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

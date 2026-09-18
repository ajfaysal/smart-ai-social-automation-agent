"""Build a Kaggle GPU notebook for the real end-to-end Chinese drama dubbing run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_notebook(video_url: str, repo: str, ref: str, language: str = "Bangla") -> dict:
    source = """import json, os, shutil, subprocess
from pathlib import Path

REPO = Path('/kaggle/working/repo')
INPUT = REPO / 'validation-input' / 'source.mp4'
CLEAN_VIDEO = REPO / 'validation-input' / 'cleaned-video.mp4'
CLEAN_REPORT = REPO / 'validation-artifacts' / 'text-cleanup.json'
ARTIFACTS = Path('/kaggle/working/final-artifacts')
ARTIFACTS.mkdir(parents=True, exist_ok=True)

try:
    from kaggle_secrets import UserSecretsClient
    _secrets = UserSecretsClient()
    def secret(name, required=False):
        try:
            value = _secrets.get_secret(name)
        except Exception:
            value = ''
        if required and not value:
            raise RuntimeError(f'Missing Kaggle Secret: {name}')
        return value
except Exception:
    def secret(name, required=False):
        value = os.getenv(name, '')
        if required and not value:
            raise RuntimeError(f'Missing runtime secret: {name}')
        return value

os.environ['OPENAI_API_KEY'] = secret('OPENAI_API_KEY', required=True)
os.environ['LIPSYNC_PROVIDER'] = 'wav2lip'
os.environ['FACE_DETECTOR'] = 'opencv-haar'
os.environ['MOUTH_LANDMARK_PROVIDER'] = 'mediapipe'

subprocess.run(['git', 'clone', '--depth', '1', '--branch', __REF__, 'https://github.com/__REPO__.git', str(REPO)], check=True)
subprocess.run(['pip', 'install', '-r', 'requirements.txt', '-r', 'requirements-cloud-runner.txt'], cwd=REPO, check=True)
if __LANGUAGE__ == 'Bangla':
    subprocess.run(['pip', 'install', '-q', 'edge-tts>=7.0,<8'], check=True)
subprocess.run(['python', 'run_cloud_smoke.py', __VIDEO_URL__, '--output', str(INPUT), '--report', str(REPO / 'validation-artifacts' / 'cloud-input.json')], cwd=REPO, check=True)

cleanup_code = "from pathlib import Path; from scene_analysis import detect_shots; from video_text_cleaner import clean_video; p=Path('validation-input/source.mp4'); cuts=[x['time'] for x in detect_shots(p)]; clean_video(p, Path('validation-input/cleaned-video.mp4'), Path('validation-artifacts/text-cleanup.json'), languages=['ch_sim','en'], scene_cuts=cuts)"
subprocess.run(['python', '-c', cleanup_code], cwd=REPO, check=True)
MUXED = REPO / 'validation-input' / 'cleaned-with-audio.mp4'
subprocess.run(['ffmpeg', '-y', '-i', str(CLEAN_VIDEO), '-i', str(INPUT), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(MUXED)], check=True)

# Speaker-aware Chinese dubbing: Demucs vocals -> diarization -> reference clips -> TTS routes.
from demucs_provider import separate_vocals
from chinese_dubbing_orchestrator import prepare_speaker_aware_dubbing
from speaker_identity import run_diarization_command

SOURCE_AUDIO = REPO / 'validation-input' / 'speaker-audio.wav'
SPEAKER_MANIFEST = REPO / 'validation-artifacts' / 'speaker-identity.json'
ROUTING_MANIFEST = REPO / 'validation-artifacts' / 'speaker-routing.json'
REFERENCE_DIR = Path('/kaggle/working/reference-voices')
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
subprocess.run(['ffmpeg', '-y', '-i', str(INPUT), '-vn', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(SOURCE_AUDIO)], check=True)
VOCALS = separate_vocals(SOURCE_AUDIO, Path('/kaggle/working/demucs-speaker'))
from drama_dubbing import transcribe as _speaker_transcribe
speaker_transcript = _speaker_transcribe(VOCALS)
speaker_segments = []
for item in speaker_transcript.get('segments', []):
    start = float(item.get('start', 0)); end = float(item.get('end', 0)); text = str(item.get('text', '')).strip()
    if end - start >= 0.05 and text:
        speaker_segments.append((start, end, text))

speaker_backend = os.getenv('CHINESE_DIARIZATION_BACKEND', 'pyannote')
identity_payload = prepare_speaker_aware_dubbing(
    VOCALS,
    speaker_segments,
    speaker_backend,
    SPEAKER_MANIFEST,
    REFERENCE_DIR,
)
ROUTED_SEGMENTS = identity_payload['segments']
SPEAKER_ROUTES = {int(x['index']): x for x in ROUTED_SEGMENTS if x.get('routing_status') == 'SUCCEEDED'}
# Reuse the exact transcript that was timestamp-routed above. This prevents a second
# transcription pass from producing different segment indices and breaking speaker routes.
_canonical_segments = tuple(speaker_segments)
_original_transcribe = drama_dubbing.transcribe if 'drama_dubbing' in globals() else None
# drama_dubbing is imported below; install the override immediately after that import.
ROUTING_MANIFEST.write_text(json.dumps(identity_payload, ensure_ascii=False, indent=2), encoding='utf-8')

wav_repo = Path('/kaggle/working/Wav2Lip')
subprocess.run(['git', 'clone', '--depth', '1', 'https://github.com/Rudrabha/Wav2Lip.git', str(wav_repo)], check=True)
subprocess.run(['pip', 'install', '-r', 'requirements.txt'], cwd=wav_repo, check=True)
ckpt_url = secret('WAV2LIP_CHECKPOINT_URL', required=True)
s3fd_url = secret('WAV2LIP_S3FD_URL', required=True)
subprocess.run(['mkdir', '-p', str(wav_repo / 'checkpoints'), str(wav_repo / 'face_detection' / 'detection' / 'sfd')], check=True)
subprocess.run(['wget', '-q', '-O', str(wav_repo / 'checkpoints' / 'wav2lip.pth'), ckpt_url], check=True)
subprocess.run(['wget', '-q', '-O', str(wav_repo / 'face_detection' / 'detection' / 'sfd' / 's3fd.pth'), s3fd_url], check=True)

wrapper = Path('/kaggle/working/wav2lip')
wrapper.write_text('#!/bin/sh\\nset -eu\\nVIDEO=\\\"\\\"; AUDIO=\\\"\\\"; CKPT=\\\"\\\"; OUT=\\\"\\\"\\nwhile [ $# -gt 0 ]; do\\n  case \\\"$1\\\" in\\n    --video) VIDEO=\\\"$2\\\"; shift 2;;\\n    --audio) AUDIO=\\\"$2\\\"; shift 2;;\\n    --checkpoint) CKPT=\\\"$2\\\"; shift 2;;\\n    --outfile) OUT=\\\"$2\\\"; shift 2;;\\n    *) echo \\\"unknown arg: $1\\\" >&2; exit 2;;\\n  esac\\ndone\\nexec python /kaggle/working/Wav2Lip/inference.py --checkpoint_path \\\"$CKPT\\\" --face \\\"$VIDEO\\\" --audio \\\"$AUDIO\\\" --outfile \\\"$OUT\\\"\\n', encoding='utf-8')
wrapper.chmod(0o755)
os.environ['WAV2LIP_COMMAND'] = str(wrapper)
os.environ['WAV2LIP_MODEL_PATH'] = str(wav_repo / 'checkpoints' / 'wav2lip.pth')

import drama_dubbing
# The diarized transcript is the canonical execution timeline. dub_video() must not
# re-transcribe the muxed source audio, because even small segmentation changes can
# misalign speaker routes. Preserve the exact routed segment indices/timestamps.
drama_dubbing.transcribe = lambda _audio_path: {
    'segments': [{'start': s[0], 'end': s[1], 'text': s[2]} for s in _canonical_segments]
}
from tts_provider import synthesize_bangla

BANGLA_CHARACTER_VOICE_POOL = [
    'bn_c01_f_young', 'bn_c02_m_young', 'bn_c03_f_adult', 'bn_c04_m_adult',
    'bn_c05_f_mature', 'bn_c06_m_mature', 'bn_c07_f_soft', 'bn_c08_m_deep',
    'bn_c09_f_energetic', 'bn_c10_m_energetic',
]

def _profile_from_hint(hint, character_index):
    hint = str(hint or '').strip().lower()
    exact = {p.lower(): p for p in BANGLA_CHARACTER_VOICE_POOL}
    if hint in exact:
        return exact[hint]
    if any(x in hint for x in ('female', 'woman', 'girl', 'mother', 'sister')):
        return BANGLA_CHARACTER_VOICE_POOL[(character_index * 2) % len(BANGLA_CHARACTER_VOICE_POOL)]
    if any(x in hint for x in ('male', 'man', 'boy', 'father', 'brother')):
        return BANGLA_CHARACTER_VOICE_POOL[((character_index * 2) + 1) % len(BANGLA_CHARACTER_VOICE_POOL)]
    return BANGLA_CHARACTER_VOICE_POOL[character_index % len(BANGLA_CHARACTER_VOICE_POOL)]

_original_director_plan = drama_dubbing.director_plan

def bangla_director_plan(segments):
    plan = _original_director_plan(segments)
    slots = {}
    for i, info in plan.items():
        char = str(info.get('character') or f'C{i+1}')
        slots.setdefault(char, len(slots))
        info['profile'] = _profile_from_hint(info.get('profile'), slots[char])
    return plan

def natural_bangla_tts(text, out_path, voice, emotion, character_id=None, reference_audio=None):
    synthesize_bangla(text, Path(out_path), profile=voice, character_id=character_id, reference_audio=reference_audio)

def quality_master_mix(background, dubbed, music, total, work):
    out = Path(work) / 'master.wav'
    subprocess.run(['ffmpeg', '-y', '-i', str(dubbed), '-filter_complex', '[0:a]highpass=f=75,lowpass=f=15000,acompressor=threshold=0.25:ratio=2:attack=20:release=180:makeup=1.0,alimiter=limit=0.94,loudnorm=I=-16:TP=-1.5:LRA=8,alimiter=limit=0.95[a]', '-map', '[a]', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', '-t', f'{total:.3f}', str(out)], check=True)
    return out

if __LANGUAGE__ == 'Bangla':
    drama_dubbing.VOICE_POOL = BANGLA_CHARACTER_VOICE_POOL
    drama_dubbing.director_plan = bangla_director_plan
    drama_dubbing.make_tts = natural_bangla_tts
    drama_dubbing.master_mix = quality_master_mix

output, mood, lip = drama_dubbing.dub_video(MUXED, __LANGUAGE__, requested_voice='auto', preserve_background=False, add_mood_music=False, lip_sync=True, speaker_routing=SPEAKER_ROUTES)
manifest = output.with_suffix('.json')
subtitle = output.with_suffix('.srt')
for path in (output, manifest, subtitle):
    if path.exists(): shutil.copy2(path, ARTIFACTS / path.name)
if CLEAN_REPORT.exists(): shutil.copy2(CLEAN_REPORT, ARTIFACTS / CLEAN_REPORT.name)
if SPEAKER_MANIFEST.exists(): shutil.copy2(SPEAKER_MANIFEST, ARTIFACTS / SPEAKER_MANIFEST.name)
if ROUTING_MANIFEST.exists(): shutil.copy2(ROUTING_MANIFEST, ARTIFACTS / ROUTING_MANIFEST.name)

report = {
    'status': 'certified' if output.exists() and manifest.exists() and lip and lip.get('applied') and identity_payload['identity'].get('status') == 'SUCCEEDED' and SPEAKER_ROUTES else 'failed_closed',
    'output': str(ARTIFACTS / output.name),
    'manifest': str(ARTIFACTS / manifest.name),
    'subtitle': str(ARTIFACTS / subtitle.name),
    'text_cleanup_report': str(ARTIFACTS / CLEAN_REPORT.name),
    'speaker_identity_manifest': str(ARTIFACTS / SPEAKER_MANIFEST.name),
    'speaker_routing_manifest': str(ARTIFACTS / ROUTING_MANIFEST.name),
    'speaker_identity_status': identity_payload['identity'].get('status'),
    'speaker_count': identity_payload['identity'].get('speaker_count', 0),
    'mood': mood,
    'lip_sync': lip,
    'voice_engine': 'multi-engine-bangla' if __LANGUAGE__ == 'Bangla' else 'canonical-openai',
    'character_voice_profiles': BANGLA_CHARACTER_VOICE_POOL if __LANGUAGE__ == 'Bangla' else [],
    'audio_mix': 'replacement-dialogue-only-no-original-music',
    'original_dialogue_removed': True,
    'original_music_removed': True,
    'source_text_cleanup': 'ocr-guided-easyocr-opencv-inpaint',
    'speaker_routing': 'diarized-speaker-to-character-to-voice-profile/reference-audio',
}
(ARTIFACTS / 'cloud-provider-certification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
"""
    source = source.replace("__REF__", repr(ref)).replace("__REPO__", repo).replace("__VIDEO_URL__", repr(video_url)).replace("__LANGUAGE__", repr(language))
    return {
        "cells": [{"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(True)}],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--video-url", required=True)
    p.add_argument("--repo", default="ajfaysal/smart-ai-social-automation-agent")
    p.add_argument("--ref", default="main")
    p.add_argument("--language", default="Bangla", choices=["Bangla", "English", "Hindi"])
    p.add_argument("--output", default="kaggle_full_pipeline.ipynb")
    args = p.parse_args()
    notebook = build_notebook(args.video_url, args.repo, args.ref, args.language)
    Path(args.output).write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

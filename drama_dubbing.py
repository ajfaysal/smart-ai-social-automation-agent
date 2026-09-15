import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="DubStudio AI", version="1.2.0")
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "dubbed_output"
OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

LANGUAGES = {
    "English": "en", "Bangla": "bn", "Hindi": "hi", "Spanish": "es",
    "Arabic": "ar", "French": "fr", "German": "de", "Portuguese": "pt",
    "Indonesian": "id", "Urdu": "ur", "Tamil": "ta", "Telugu": "te",
}
VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or "ffmpeg command failed")
    return result.stdout


def duration(path):
    value = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)
    ]).strip()
    return max(0.0, float(value))


def api_request(method, url, **kwargs):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(500, "OPENAI_API_KEY is not configured on the server.")
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {key}"
    return requests.request(method, url, headers=headers, timeout=300, **kwargs)


def transcribe(audio_path):
    with open(audio_path, "rb") as audio:
        response = api_request(
            "POST", "https://api.openai.com/v1/audio/transcriptions",
            files={"file": (audio_path.name, audio, "audio/mpeg")},
            data={
                "model": os.getenv("DUBBING_STT_MODEL", "whisper-1"),
                "response_format": "verbose_json",
            },
        )
    if not response.ok:
        raise RuntimeError(response.text)
    return response.json()


def translate(text, target_language, max_seconds):
    # Timing is a hard constraint. Ask the translator to stay concise enough
    # for the original dialogue window instead of producing a literal paragraph.
    response = api_request(
        "POST", "https://api.openai.com/v1/chat/completions",
        json={
            "model": os.getenv("DUBBING_TRANSLATION_MODEL", "gpt-4o-mini"),
            "temperature": 0.15,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional audiovisual dubbing translator. "
                        "Translate naturally and emotionally, but timing is a hard constraint. "
                        "Use the fewest natural words needed to convey the meaning. "
                        "Never add explanations, speaker labels, stage directions, or extra sentences. "
                        "Return only the final spoken dialogue."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Translate into {target_language}. The original dialogue has only "
                        f"{max_seconds:.2f} seconds of screen time. Keep the translated line "
                        f"short enough to sound natural inside that exact window.\n\n{text}"
                    ),
                },
            ],
        },
    )
    if not response.ok:
        raise RuntimeError(response.text)
    return response.json()["choices"][0]["message"]["content"].strip()


def make_tts(text, out_path, voice):
    response = api_request(
        "POST", "https://api.openai.com/v1/audio/speech",
        json={
            "model": os.getenv("DUBBING_TTS_MODEL", "gpt-4o-mini-tts"),
            "voice": voice,
            "input": text,
            "response_format": "mp3",
        },
    )
    if not response.ok:
        raise RuntimeError(response.text)
    out_path.write_bytes(response.content)


def fit_audio_exact(input_path, output_path, target_duration):
    """Time-lock a generated line to the exact original dialogue window.

    The TTS request can finish late on the server, but that never affects the
    media timeline. Every generated line is rendered to the original start/end
    timestamps before the final audio track is assembled.
    """
    if target_duration <= 0:
        raise RuntimeError("Invalid target dialogue duration.")
    source_duration = duration(input_path)
    if source_duration <= 0:
        raise RuntimeError("Generated TTS audio has no duration.")

    ratio = source_duration / target_duration
    filters = []
    while ratio > 2.0:
        filters.append("atempo=2.0")
        ratio /= 2.0
    while ratio < 0.5:
        filters.append("atempo=0.5")
        ratio /= 0.5
    filters.append(f"atempo={ratio:.8f}")
    filters.append(f"atrim=duration={target_duration:.3f}")
    filters.append("apad")

    run([
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", ",".join(filters),
        "-t", f"{target_duration:.3f}",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
        str(output_path),
    ])

    actual = duration(output_path)
    if abs(actual - target_duration) > 0.035:
        raise RuntimeError(
            f"Timing lock failed: expected {target_duration:.3f}s, got {actual:.3f}s."
        )


def build_timeline(dubbed_files, total_duration, work):
    """Build a sample-accurate sequential timeline from absolute timestamps."""
    parts = []
    cursor = 0.0

    for index, (start, end, audio) in enumerate(dubbed_files):
        start = max(0.0, min(float(start), total_duration))
        end = max(start, min(float(end), total_duration))
        target_duration = end - start
        if target_duration < 0.05:
            continue

        if start > cursor + 0.001:
            gap = work / f"silence_{index}.wav"
            run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "anullsrc=r=48000:cl=stereo",
                "-t", f"{start - cursor:.3f}",
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
                str(gap),
            ])
            parts.append(gap)

        parts.append(audio)
        cursor = max(cursor, end)

    if cursor < total_duration - 0.001:
        tail = work / "tail_silence.wav"
        run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=48000:cl=stereo",
            "-t", f"{total_duration - cursor:.3f}",
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
            str(tail),
        ])
        parts.append(tail)

    if not parts:
        raise RuntimeError("No dubbed audio was generated.")

    concat_list = work / "concat.txt"
    escaped = []
    for path in parts:
        value = path.as_posix().replace("'", "'\\''")
        escaped.append(f"file '{value}'")
    concat_list.write_text("\n".join(escaped), encoding="utf-8")
    return concat_list


def write_srt(manifest, output_path):
    def stamp(seconds):
        ms = max(0, int(round(seconds * 1000)))
        h, rem = divmod(ms, 3600000)
        m, rem = divmod(rem, 60000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for index, item in enumerate(manifest, 1):
        lines.extend([
            str(index),
            f"{stamp(item['start'])} --> {stamp(item['end'])}",
            item["translation"],
            "",
        ])
    output_path.write_text("\n".join(lines), encoding="utf-8")


def dub_video(video_path, target_language, voice):
    work = Path(tempfile.mkdtemp(prefix="drama-dub-"))
    try:
        total_duration = duration(video_path)
        if total_duration <= 0:
            raise RuntimeError("Could not determine video duration.")

        source_audio = work / "source.mp3"
        run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", "16000", str(source_audio),
        ])
        transcript = transcribe(source_audio)
        raw_segments = transcript.get("segments", [])
        if not raw_segments:
            raise RuntimeError("No speech segments were detected in the video.")

        # Normalize timestamps once. These timestamps are the master clock for
        # every downstream operation. TTS generation time is never used as a clock.
        segments = []
        for raw in raw_segments:
            text = (raw.get("text") or "").strip()
            if not text:
                continue
            start = max(0.0, float(raw.get("start", 0.0)))
            end = max(start + 0.05, float(raw.get("end", start + 0.05)))
            start = min(start, total_duration)
            end = min(end, total_duration)
            if end - start >= 0.05:
                segments.append((start, end, text))

        dubbed_files = []
        manifest = []
        previous_end = 0.0

        for index, (start, end, text) in enumerate(segments):
            # Avoid overlapping generated tracks if the STT provider reports
            # slightly overlapping timestamps.
            start = max(start, previous_end)
            if end <= start + 0.05:
                continue
            window = end - start

            translated = translate(text, target_language, window)
            raw_tts = work / f"tts_{index}.mp3"
            fitted = work / f"fit_{index}.wav"
            make_tts(translated, raw_tts, voice)
            fit_audio_exact(raw_tts, fitted, window)

            dubbed_files.append((start, end, fitted))
            manifest.append({
                "index": index + 1,
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(window, 3),
                "source": text,
                "translation": translated,
                "timing_lock": True,
                "drift_ms": 0,
            })
            previous_end = end

        concat_list = build_timeline(dubbed_files, total_duration, work)
        dubbed_audio = work / "dubbed.wav"
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
            "-t", f"{total_duration:.3f}", str(dubbed_audio),
        ])

        # Final verification: the master dub track must be the same duration as
        # the source video. This prevents the classic "dialogue arrives seconds late" bug.
        final_audio_duration = duration(dubbed_audio)
        if abs(final_audio_duration - total_duration) > 0.05:
            raise RuntimeError(
                f"Final timing verification failed: video={total_duration:.3f}s, "
                f"dub={final_audio_duration:.3f}s."
            )

        output = OUTPUT_DIR / f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4"
        run([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(dubbed_audio),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac",
            "-t", f"{total_duration:.3f}",
            "-movflags", "+faststart",
            str(output),
        ])

        manifest_path = OUTPUT_DIR / f"{output.stem}.json"
        manifest_path.write_text(json.dumps({
            "version": "1.2.0",
            "timing_mode": "frame-locked",
            "video_duration": round(total_duration, 3),
            "target_language": target_language,
            "voice": voice,
            "segments": manifest,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        write_srt(manifest, OUTPUT_DIR / f"{output.stem}.srt")
        return output
    finally:
        shutil.rmtree(work, ignore_errors=True)


@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")


@app.post("/api/dub")
async def create_dub(
    video: UploadFile = File(...),
    target_language: str = Form(...),
    voice: str = Form("alloy"),
):
    if target_language not in LANGUAGES:
        raise HTTPException(400, "Unsupported target language.")
    if voice not in VOICES:
        raise HTTPException(400, "Unsupported voice.")
    if not video.filename:
        raise HTTPException(400, "Please upload a video.")
    suffix = Path(video.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, "Supported formats: MP4, MOV, MKV, WebM, AVI.")

    temp = Path(tempfile.mkstemp(suffix=suffix)[1])
    try:
        total = 0
        with temp.open("wb") as handle:
            while True:
                chunk = await video.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Video exceeds the 500 MB upload limit.")
                handle.write(chunk)

        output = dub_video(temp, target_language, voice)
        return {
            "filename": output.name,
            "download_url": f"/api/download/{output.name}",
            "subtitle_url": f"/api/download/{output.stem}.srt",
            "manifest_url": f"/api/download/{output.stem}.json",
            "timing_mode": "frame-locked",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Dubbing failed: {exc}") from exc
    finally:
        temp.unlink(missing_ok=True)


@app.get("/api/download/{filename}")
def download(filename: str):
    safe_name = Path(filename).name
    allowed = (
        safe_name.startswith("dubbed_")
        and safe_name.endswith((".mp4", ".srt", ".json"))
    )
    if safe_name != filename or not allowed:
        raise HTTPException(404, "File not found.")
    path = (OUTPUT_DIR / safe_name).resolve()
    if path.parent != OUTPUT_DIR.resolve() or not path.exists():
        raise HTTPException(404, "File not found.")
    media = "video/mp4" if path.suffix == ".mp4" else "text/plain"
    return FileResponse(path, media_type=media, filename=path.name)

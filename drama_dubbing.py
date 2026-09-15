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

app = FastAPI(title="DubStudio AI", version="1.1.0")
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
    value = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)]).strip()
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
            data={"model": os.getenv("DUBBING_STT_MODEL", "whisper-1"), "response_format": "verbose_json"},
        )
    if not response.ok:
        raise RuntimeError(response.text)
    return response.json()


def translate(text, target_language):
    response = api_request(
        "POST", "https://api.openai.com/v1/chat/completions",
        json={
            "model": os.getenv("DUBBING_TRANSLATION_MODEL", "gpt-4o-mini"),
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "You are a professional audiovisual dubbing translator. Keep dialogue natural, emotionally faithful, concise enough for the original timing, and preserve names and cultural context. Return only the translated dialogue."},
                {"role": "user", "content": f"Translate into {target_language}:\n{text}"},
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


def fit_audio(input_path, output_path, target_duration):
    source_duration = duration(input_path)
    if source_duration <= 0 or target_duration <= 0:
        raise RuntimeError("Invalid audio duration.")
    ratio = source_duration / target_duration
    filters = []
    while ratio > 2.0:
        filters.append("atempo=2.0")
        ratio /= 2.0
    while ratio < 0.5:
        filters.append("atempo=0.5")
        ratio /= 0.5
    filters.append(f"atempo={ratio:.6f}")
    run(["ffmpeg", "-y", "-i", str(input_path), "-af", ",".join(filters), "-t", f"{target_duration:.3f}", "-ar", "48000", "-ac", "2", str(output_path)])


def build_timeline(dubbed_files, total_duration, work):
    parts = []
    cursor = 0.0
    for index, (start, audio) in enumerate(dubbed_files):
        start = max(0.0, start)
        if start > cursor + 0.01:
            gap = work / f"silence_{index}.wav"
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{start - cursor:.3f}", str(gap)])
            parts.append(gap)
            cursor = start
        parts.append(audio)
        cursor = start + duration(audio)
    if cursor < total_duration:
        tail = work / "tail_silence.wav"
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{total_duration - cursor:.3f}", str(tail)])
        parts.append(tail)
    if not parts:
        raise RuntimeError("No dubbed audio was generated.")
    concat_list = work / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p.as_posix().replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'" for p in parts), encoding="utf-8")
    return concat_list


def dub_video(video_path, target_language, voice):
    work = Path(tempfile.mkdtemp(prefix="drama-dub-"))
    try:
        total_duration = duration(video_path)
        source_audio = work / "source.mp3"
        run(["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(source_audio)])
        transcript = transcribe(source_audio)
        segments = transcript.get("segments", [])
        if not segments:
            raise RuntimeError("No speech segments were detected in the video.")

        dubbed_files = []
        manifest = []
        for index, segment in enumerate(segments):
            text = (segment.get("text") or "").strip()
            if not text:
                continue
            start = max(0.0, float(segment.get("start", 0)))
            end = max(start + 0.25, float(segment.get("end", start + 0.25)))
            target = min(total_duration, end)
            segment_duration = max(0.25, target - start)
            translated = translate(text, target_language)
            raw_tts = work / f"tts_{index}.mp3"
            fitted = work / f"fit_{index}.wav"
            make_tts(translated, raw_tts, voice)
            fit_audio(raw_tts, fitted, segment_duration)
            dubbed_files.append((start, fitted))
            manifest.append({"start": start, "end": target, "source": text, "translation": translated})

        concat_list = build_timeline(dubbed_files, total_duration, work)
        dubbed_audio = work / "dubbed.wav"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-ar", "48000", "-ac", "2", str(dubbed_audio)])

        output = OUTPUT_DIR / f"dubbed_{LANGUAGES[target_language]}_{uuid.uuid4().hex[:10]}.mp4"
        # Keep the original video stream and replace the audio with the full-length timed dub.
        run(["ffmpeg", "-y", "-i", str(video_path), "-i", str(dubbed_audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-t", f"{total_duration:.3f}", str(output)])
        (OUTPUT_DIR / f"{output.stem}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return output
    finally:
        shutil.rmtree(work, ignore_errors=True)


@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")


@app.post("/api/dub")
async def create_dub(video: UploadFile = File(...), target_language: str = Form(...), voice: str = Form("alloy")):
    if target_language not in LANGUAGES:
        raise HTTPException(400, "Unsupported target language.")
    if voice not in VOICES:
        raise HTTPException(400, "Unsupported voice.")
    if not video.filename:
        raise HTTPException(400, "Please upload a video.")
    suffix = Path(video.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, "Supported formats: MP4, MOV, MKV, WebM, AVI.")
    content = await video.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Video exceeds the 500 MB upload limit.")
    temp = Path(tempfile.mkstemp(suffix=suffix)[1])
    try:
        temp.write_bytes(content)
        output = dub_video(temp, target_language, voice)
        return {"filename": output.name, "download_url": f"/api/download/{output.name}"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Dubbing failed: {exc}") from exc
    finally:
        temp.unlink(missing_ok=True)


@app.get("/api/download/{filename}")
def download(filename: str):
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.startswith("dubbed_") or not safe_name.endswith(".mp4"):
        raise HTTPException(404, "File not found.")
    path = (OUTPUT_DIR / safe_name).resolve()
    if path.parent != OUTPUT_DIR.resolve() or not path.exists():
        raise HTTPException(404, "File not found.")
    return FileResponse(path, media_type="video/mp4", filename=path.name)

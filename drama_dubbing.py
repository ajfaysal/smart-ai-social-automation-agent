import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Drama Dubbing Tool", version="1.0.0")
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "dubbed_output"
OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

LANGUAGES = {
    "English": "en", "Bangla": "bn", "Hindi": "hi", "Spanish": "es",
    "Arabic": "ar", "French": "fr", "German": "de", "Portuguese": "pt",
    "Indonesian": "id", "Urdu": "ur", "Tamil": "ta", "Telugu": "te",
}


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    return result.stdout


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
    prompt = (
        f"Translate this drama dialogue into {target_language}. Preserve meaning, emotion, names, "
        "and conversational tone. Return only the translated dialogue.\n\n" + text
    )
    response = api_request(
        "POST", "https://api.openai.com/v1/chat/completions",
        json={"model": os.getenv("DUBBING_TRANSLATION_MODEL", "gpt-4o-mini"),
              "temperature": 0.2,
              "messages": [{"role": "system", "content": "You are a professional audiovisual dubbing translator."},
                           {"role": "user", "content": prompt}]},
    )
    if not response.ok:
        raise RuntimeError(response.text)
    return response.json()["choices"][0]["message"]["content"].strip()


def make_tts(text, out_path, voice):
    response = api_request(
        "POST", "https://api.openai.com/v1/audio/speech",
        json={"model": os.getenv("DUBBING_TTS_MODEL", "gpt-4o-mini-tts"), "voice": voice,
              "input": text, "response_format": "mp3"},
    )
    if not response.ok:
        raise RuntimeError(response.text)
    out_path.write_bytes(response.content)


def fit_audio(input_path, output_path, duration):
    # Keep each dubbed segment close to the original timing without extreme pitch changes.
    probe = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(input_path)]).strip())
    if probe <= 0 or duration <= 0:
        shutil.copyfile(input_path, output_path)
        return
    ratio = probe / duration
    if 0.5 <= ratio <= 2.0:
        filters = f"atempo={ratio:.6f}"
        run(["ffmpeg", "-y", "-i", str(input_path), "-filter:a", filters, "-t", f"{duration:.3f}", str(output_path)])
    else:
        # Pad or trim when stretching would be unnatural.
        run(["ffmpeg", "-y", "-i", str(input_path), "-af", "apad", "-t", f"{duration:.3f}", str(output_path)])


def dub_video(video_path, target_language, voice):
    work = Path(tempfile.mkdtemp(prefix="drama-dub-"))
    try:
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
            start = float(segment.get("start", 0))
            end = float(segment.get("end", start))
            duration = max(0.25, end - start)
            translated = translate(text, target_language)
            raw_tts = work / f"tts_{index}.mp3"
            fitted = work / f"fit_{index}.wav"
            make_tts(translated, raw_tts, voice)
            fit_audio(raw_tts, fitted, duration)
            dubbed_files.append((start, fitted))
            manifest.append({"start": start, "end": end, "source": text, "translation": translated})

        concat_list = work / "concat.txt"
        # Build a timeline using silence gaps so dialogue stays aligned with the original.
        parts = []
        cursor = 0.0
        for start, audio in dubbed_files:
            gap = max(0.0, start - cursor)
            if gap:
                silence = work / f"silence_{len(parts)}.wav"
                run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", f"{gap:.3f}", str(silence)])
                parts.append(silence)
            parts.append(audio)
            dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio)]).strip())
            cursor = start + dur
        concat_list.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts), encoding="utf-8")
        dubbed_audio = work / "dubbed.wav"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-ar", "48000", "-ac", "2", str(dubbed_audio)])

        output = OUTPUT_DIR / f"{video_path.stem}_{LANGUAGES[target_language]}_dubbed.mp4"
        run(["ffmpeg", "-y", "-i", str(video_path), "-i", str(dubbed_audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", str(output)])
        (OUTPUT_DIR / f"{output.stem}.json").write_text(__import__("json").dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
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
    if not video.filename:
        raise HTTPException(400, "Please upload a video.")
    suffix = Path(video.filename).suffix.lower()
    if suffix not in {".mp4", ".mov", ".mkv", ".webm", ".avi"}:
        raise HTTPException(400, "Supported formats: MP4, MOV, MKV, WebM, AVI.")
    temp = Path(tempfile.mkstemp(suffix=suffix)[1])
    try:
        temp.write_bytes(await video.read())
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
    path = (OUTPUT_DIR / filename).resolve()
    if path.parent != OUTPUT_DIR.resolve() or not path.exists():
        raise HTTPException(404, "File not found.")
    return FileResponse(path, media_type="video/mp4", filename=path.name)

"""Asynchronous production API surface for the dubbing engine.

Run with: uvicorn production_api:app --host 0.0.0.0 --port 8000
The legacy synchronous API in drama_dubbing.py remains available for
compatibility; this surface is intended for the future web application.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from drama_dubbing import (
    LANGUAGES,
    MAX_UPLOAD_BYTES,
    SUPPORTED_EXTENSIONS,
    VOICES,
    dub_video,
)
from job_manager import job_manager

app = FastAPI(title="DubStudio AI Production API", version="1.0.0")


def _run_dub(temp_path: Path, target_language: str, voice: str, preserve_background: bool, add_mood_music: bool, lip_sync: bool) -> dict:
    try:
        output, dominant, lip = dub_video(
            temp_path,
            target_language,
            voice,
            preserve_background,
            add_mood_music,
            lip_sync,
        )
        return {
            "filename": output.name,
            "download_url": f"/api/download/{output.name}",
            "subtitle_url": f"/api/download/{output.stem}.srt",
            "manifest_url": f"/api/download/{output.stem}.json",
            "dominant_mood": dominant,
            "lip_sync_applied": bool(lip and lip.get("applied")),
            "lip_sync_provider": lip.get("provider", "disabled") if lip else "disabled",
        }
    finally:
        temp_path.unlink(missing_ok=True)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "production-api", "version": "1.0.0"}


@app.post("/api/jobs")
async def create_job(
    video: UploadFile = File(...),
    target_language: str = Form(...),
    voice: str = Form("auto"),
    preserve_background: bool = Form(True),
    add_mood_music: bool = Form(True),
    lip_sync: bool = Form(False),
) -> dict:
    if target_language not in LANGUAGES:
        raise HTTPException(400, "Unsupported target language.")
    if voice != "auto" and voice not in VOICES:
        raise HTTPException(400, "Unsupported voice.")
    suffix = Path(video.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, "Supported formats: MP4, MOV, MKV, WebM, AVI.")

    fd, name = tempfile.mkstemp(prefix="dub_upload_", suffix=suffix)
    Path(name).unlink(missing_ok=True)
    temp = Path(name)
    total = 0
    try:
        with temp.open("wb") as out:
            while True:
                chunk = await video.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Video exceeds the 500 MB upload limit.")
                out.write(chunk)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    finally:
        await video.close()

    job_id = job_manager.submit(
        _run_dub,
        temp,
        target_language,
        voice,
        preserve_background,
        add_mood_music,
        lip_sync,
    )
    return {"job_id": job_id, "state": "queued", "status_url": f"/api/jobs/{job_id}"}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    return job

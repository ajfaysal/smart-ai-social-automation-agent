# Production web API

The repository now exposes `production_api.py` as the web-app backend contract.
It keeps the existing synchronous `/api/dub` route for compatibility while adding
an asynchronous job surface for real web clients.

## Run

```bash
uvicorn production_api:app --host 0.0.0.0 --port 8000
```

## Flow

1. `POST /api/jobs` uploads the video and returns a `job_id` immediately.
2. `GET /api/jobs/{job_id}` reports `queued`, `running`, `succeeded`, or `failed`.
3. A successful result contains MP4, SRT, and manifest download URLs.
4. `GET /api/download/{filename}` serves only generated `dubbed_*` artifacts.

`DUB_JOB_WORKERS` controls the bounded in-process worker count and defaults to 1.
The manager is deliberately dependency-free; production deployments can later
replace it with a durable Redis/Celery-style queue without changing the HTTP
job contract.

This is the backend foundation for the future upload/progress/result web UI.
It does not claim distributed durability or GPU scheduling by itself.

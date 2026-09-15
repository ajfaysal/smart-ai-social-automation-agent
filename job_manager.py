"""Small production-safe job manager for the FastAPI dubbing surface.

The manager intentionally has no external dependency: it provides a bounded
worker pool and auditable job state for a single process. A future deployment
can replace this adapter with Redis/Celery without changing the HTTP contract.
"""
from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    id: str
    state: str = "queued"
    created_at: str = field(default_factory=_now)
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "job_id": self.id,
            "state": self.state,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
        }


class JobManager:
    def __init__(self, max_workers: int | None = None) -> None:
        workers = max_workers or int(os.getenv("DUB_JOB_WORKERS", "1"))
        self._executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="dub-job")
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, fn: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> str:
        job_id = uuid.uuid4().hex
        job = Job(id=job_id)
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run, job_id, fn, args, kwargs)
        return job_id

    def _run(self, job_id: str, fn: Callable[..., dict[str, Any]], args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.state = "running"
            job.started_at = _now()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - job boundary must be auditable
            with self._lock:
                job.state = "failed"
                job.error = str(exc)
                job.finished_at = _now()
            return
        with self._lock:
            job.state = "succeeded"
            job.result = result
            job.finished_at = _now()

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.snapshot() if job else None


job_manager = JobManager()

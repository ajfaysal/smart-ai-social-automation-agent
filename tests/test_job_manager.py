import time

from job_manager import JobManager


def test_job_manager_runs_and_exposes_terminal_state():
    manager = JobManager(max_workers=1)

    def work(value):
        time.sleep(0.01)
        return {"value": value}

    job_id = manager.submit(work, 42)
    for _ in range(100):
        snapshot = manager.get(job_id)
        if snapshot and snapshot["state"] == "succeeded":
            break
        time.sleep(0.01)

    assert snapshot is not None
    assert snapshot["state"] == "succeeded"
    assert snapshot["result"] == {"value": 42}
    assert snapshot["finished_at"] is not None


def test_job_manager_records_failures():
    manager = JobManager(max_workers=1)

    def work():
        raise RuntimeError("provider failed")

    job_id = manager.submit(work)
    for _ in range(100):
        snapshot = manager.get(job_id)
        if snapshot and snapshot["state"] == "failed":
            break
        time.sleep(0.01)

    assert snapshot is not None
    assert snapshot["state"] == "failed"
    assert snapshot["error"] == "provider failed"

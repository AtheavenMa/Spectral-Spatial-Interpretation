"""One-at-a-time background runs so the page can poll and cancel."""
from __future__ import annotations

from threading import Lock, Thread
from uuid import uuid4

from lab.runtime import HOOK, Cancelled, RunHook


class Busy(RuntimeError):
    def __init__(self, job_id: str):
        super().__init__("A run is already computing. Cancel it or wait for it to finish.")
        self.job_id = job_id


class Jobs:
    def __init__(self):
        self._lock = Lock()
        self._jobs: dict[str, dict] = {}

    def start(self, params: dict) -> str:
        hook = RunHook()
        with self._lock:
            active = next((item for item in self._jobs.values() if item["status"] == "running"), None)
            if active is not None:
                raise Busy(active["id"])
            job_id = uuid4().hex[:12]
            self._jobs[job_id] = {
                "id": job_id, "status": "running", "evaluations": 0,
                "result": None, "error": None, "hook": hook,
            }
        Thread(target=self._execute, args=(job_id, params, hook), daemon=True).start()
        return job_id

    def _execute(self, job_id: str, params: dict, hook: RunHook) -> None:
        from lab.engine import run
        token = HOOK.set(hook)
        try:
            result = run(**params)
            status, error = "done", None
        except Cancelled as exc:
            result, status, error = None, "cancelled", str(exc)
        except (ValueError, FileNotFoundError) as exc:
            result, status, error = None, "error", str(exc)
        finally:
            HOOK.reset(token)
        with self._lock:
            job = self._jobs[job_id]
            job.update(status=status, result=result, error=error, evaluations=hook.evaluations)

    def get(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            hook = job["hook"]
            evaluations = hook.evaluations if job["status"] == "running" else job["evaluations"]
            return {
                "id": job_id,
                "status": job["status"],
                "evaluations": evaluations,
                "result": job["result"],
                "error": job["error"],
            }

    def cancel(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            job["hook"].cancel.set()
        return self.get(job_id)


JOBS = Jobs()

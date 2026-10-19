"""FastAPI application for the interactive SSI Playground."""
from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import engine
from .jobs import JOBS, Busy

STATIC = Path(__file__).resolve().parent / "static"
app = FastAPI(title="SSI Playground", version="0.1.0")
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
COMPUTE_LOCK = Lock()


class ExplainRequest(BaseModel):
    model_id: str = engine.MODEL_ID
    sample_id: str = engine.SAMPLE_ID
    grid: Literal[4, 8, 16] = 8
    baseline: Literal["mean", "zero"] = "mean"
    method: Literal["auto", "exact", "permutation"] = "permutation"
    permutations: int = Field(default=10, ge=1, le=20)
    seed: int = Field(default=0, ge=0, le=100000)


@app.get("/")
def homepage():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "model_ready": engine.CHECKPOINT.is_file(),
            "sample_ready": engine.SAMPLE.is_file()}


@app.get("/api/catalog")
def get_catalog():
    return engine.catalog()


@app.get("/api/preview")
def get_preview(model_id: str = engine.MODEL_ID, sample_id: str = engine.SAMPLE_ID):
    try:
        engine._check_selection(model_id, sample_id)
        if not COMPUTE_LOCK.acquire(blocking=False):
            raise HTTPException(status_code=429, detail="Model is busy; retry shortly.")
        try:
            return engine.previews(model_id, sample_id)
        finally:
            COMPUTE_LOCK.release()
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _params(req: ExplainRequest) -> dict:
    return {
        "model_id": req.model_id, "sample_id": req.sample_id, "grid": req.grid,
        "baseline": req.baseline, "method": req.method,
        "permutations": req.permutations, "seed": req.seed,
    }


@app.post("/api/jobs")
def start_job(req: ExplainRequest):
    try:
        return {"job_id": JOBS.start(_params(req))}
    except Busy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/jobs/{job_id}")
def read_job(job_id: str):
    try:
        return JOBS.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown job.") from exc


@app.delete("/api/jobs/{job_id}")
def stop_job(job_id: str):
    try:
        return JOBS.cancel(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown job.") from exc


@app.post("/api/explain")
def compute(req: ExplainRequest):
    if not COMPUTE_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Model is busy; retry shortly.")
    try:
        try:
            return engine.run(
                req.model_id, req.sample_id, req.grid,
                req.baseline, req.method, req.permutations, req.seed,
            )
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        COMPUTE_LOCK.release()

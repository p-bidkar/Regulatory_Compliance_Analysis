"""FastAPI backend serving the RegComply web frontend.

Exposes the multi-agent pipeline as an async job API: submit a
regulation pair, poll job status/stage, read back the final result
(and browse run history) once complete.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from regcomply import __version__
from regcomply.api import db
from regcomply.api.jobs import run_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REG_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "regulations"

app = FastAPI(title="RegComply API", version=__version__)

# Local/demo scope: open CORS so the Next.js dev server (and containerized
# frontend) can call the API freely. Tighten allow_origins before any real
# multi-tenant or public deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


class RegulationPair(BaseModel):
    regulation_id: str
    baseline_path: str
    updated_path: str


class AnalyzeRequest(BaseModel):
    regulation_id: str


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/regulations", response_model=list[RegulationPair])
def list_regulations() -> list[RegulationPair]:
    """Discover baseline/updated regulation pairs available on disk."""
    pairs: dict[str, dict[str, str]] = {}
    if REG_DIR.exists():
        for path in sorted(REG_DIR.glob("*_baseline.txt")):
            reg_id = path.stem.replace("_baseline", "")
            pairs.setdefault(reg_id, {})["baseline_path"] = str(path)
        for path in sorted(REG_DIR.glob("*_updated.txt")):
            reg_id = path.stem.replace("_updated", "")
            pairs.setdefault(reg_id, {})["updated_path"] = str(path)

    return [
        RegulationPair(regulation_id=reg_id, **paths)
        for reg_id, paths in pairs.items()
        if "baseline_path" in paths and "updated_path" in paths
    ]


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    baseline_path = REG_DIR / f"{req.regulation_id}_baseline.txt"
    updated_path = REG_DIR / f"{req.regulation_id}_updated.txt"
    if not baseline_path.exists() or not updated_path.exists():
        raise HTTPException(status_code=404, detail=f"Regulation '{req.regulation_id}' not found")

    job_id = db.create_job(req.regulation_id, str(baseline_path), str(updated_path))
    background_tasks.add_task(
        run_job, job_id, req.regulation_id, str(baseline_path), str(updated_path)
    )
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs")
def list_recent_jobs(limit: int = 50) -> list[dict[str, Any]]:
    return db.list_jobs(limit=limit)

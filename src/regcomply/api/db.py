"""SQLite persistence for analysis jobs.

Backs the async job model used by the API: a job row is created when a
run is submitted, then updated as the pipeline progresses through
stages, and finally holds the full result (or error) once it finishes.
This also doubles as run history for the frontend.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "jobs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    regulation_id TEXT NOT NULL,
    baseline_path TEXT NOT NULL,
    updated_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    stage TEXT NOT NULL DEFAULT 'queued',
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)


def create_job(regulation_id: str, baseline_path: str, updated_path: str) -> str:
    job_id = str(uuid.uuid4())
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO jobs "
            "(id, regulation_id, baseline_path, updated_path, status, stage, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'pending', 'queued', ?, ?)",
            (job_id, regulation_id, baseline_path, updated_path, now, now),
        )
    return job_id


def update_job_stage(job_id: str, stage: str, status: str = "running") -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE jobs SET stage = ?, status = ?, updated_at = ? WHERE id = ?",
            (stage, status, _now(), job_id),
        )


def complete_job(job_id: str, result: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'completed', stage = 'done', result_json = ?, updated_at = ? "
            "WHERE id = ?",
            (json.dumps(result, default=str), _now(), job_id),
        )


def fail_job(job_id: str, error: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'error', stage = 'failed', error = ?, updated_at = ? WHERE id = ?",
            (error, _now(), job_id),
        )


def get_job(job_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_dict(row) if row is not None else None


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    result_json = d.pop("result_json", None)
    d["result"] = json.loads(result_json) if result_json else None
    return d

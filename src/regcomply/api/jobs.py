"""Background execution of the RegComply pipeline for the API.

Runs the LangGraph pipeline via ``stream_pipeline`` (rather than the
blocking ``run_pipeline``) so the job's ``stage`` column reflects real
progress (change detection -> policy RAG -> recommendations) that the
frontend can poll and render as a step indicator.
"""

from __future__ import annotations

import logging
from pathlib import Path

from regcomply.api import db
from regcomply.graph import stream_pipeline
from regcomply.graph.state import PipelineState

logger = logging.getLogger(__name__)

_NEXT_STAGE = {
    "change_detection": "policy_rag",
    "policy_rag": "recommendations",
    "recommendations": "finalizing",
}


def run_job(job_id: str, regulation_id: str, baseline_path: str, updated_path: str) -> None:
    try:
        baseline_text = Path(baseline_path).read_text(encoding="utf-8")
        updated_text = Path(updated_path).read_text(encoding="utf-8")

        init: PipelineState = {
            "regulation_id": regulation_id,
            "baseline_text": baseline_text,
            "updated_text": updated_text,
        }

        accumulated: dict = dict(init)
        db.update_job_stage(job_id, "change_detection")
        for node_name, node_output in stream_pipeline(init):
            accumulated.update(node_output)
            db.update_job_stage(job_id, _NEXT_STAGE.get(node_name, node_name))

        db.complete_job(job_id, accumulated)
    except Exception as exc:  # noqa: BLE001 - surfaced to the client via job status
        logger.exception("job %s failed", job_id)
        db.fail_job(job_id, str(exc))

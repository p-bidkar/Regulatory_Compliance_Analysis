"""Evaluation harness skeleton.

Runs the full pipeline against each case in the gold set and reports:
  - document-level retrieval recall (proxy for recall@k until chunk-level
    gold labels exist)
  - citation verification accuracy
  - per-stage latency (from PipelineState.timings)

A failure in any single case (missing files, LLM/network error, missing
credentials) is caught and reported as that case's status rather than
crashing the whole run, so `python -m regcomply.eval` is always safe to
invoke.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from regcomply.eval.gold import load_gold_set
from regcomply.eval.metrics import citation_accuracy, recall_at_k
from regcomply.graph import run_pipeline
from regcomply.graph.state import PipelineState

logger = logging.getLogger(__name__)


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    regulation_id = case.get("regulation_id", "unknown")
    baseline_path = Path(case["baseline_path"])
    updated_path = Path(case["updated_path"])

    result: dict[str, Any] = {
        "regulation_id": regulation_id,
        "status": "skipped",
        "recall_at_k": None,
        "citation_accuracy": None,
        "changes_detected": None,
        "chunks_retrieved": None,
        "recommendations_generated": None,
        "timings": {},
        "error": None,
    }

    if not baseline_path.exists() or not updated_path.exists():
        result["error"] = (
            f"regulation file(s) not found: {baseline_path} / {updated_path}"
        )
        return result

    init: PipelineState = {
        "regulation_id": regulation_id,
        "baseline_text": baseline_path.read_text(encoding="utf-8"),
        "updated_text": updated_path.read_text(encoding="utf-8"),
    }

    try:
        output = run_pipeline(init)
    except Exception as exc:  # noqa: BLE001 - eval must never crash on one bad case
        logger.warning("eval: pipeline run failed for %s (%s)", regulation_id, exc)
        result["status"] = "error"
        result["error"] = str(exc)
        return result

    retrieved_docs = {c.get("source_doc_id", "") for c in output.get("retrieved_chunks", [])}
    expected_docs = set(case.get("expected_relevant_docs", []))

    result["status"] = "completed"
    result["recall_at_k"] = round(recall_at_k(retrieved_docs, expected_docs), 3)
    result["citation_accuracy"] = round(citation_accuracy(output.get("citations", [])), 3)
    result["changes_detected"] = len(output.get("change_items", []))
    result["chunks_retrieved"] = len(output.get("retrieved_chunks", []))
    result["recommendations_generated"] = len(output.get("draft_recommendations", []))
    result["timings"] = output.get("timings", {})
    return result


def main() -> None:
    cases = load_gold_set()
    if not cases:
        print("eval: no gold set found at data/eval/gold_set.json")
        return

    results = [_run_case(case) for case in cases]
    completed = [r for r in results if r["status"] == "completed"]

    print(f"\nEvaluated {len(results)} case(s), {len(completed)} completed.\n")
    for r in results:
        print(json.dumps(r, indent=2))

    if completed:
        avg_recall = sum(r["recall_at_k"] for r in completed) / len(completed)
        avg_citation = sum(r["citation_accuracy"] for r in completed) / len(completed)
        print(f"\nAverage recall@k (document-level): {avg_recall:.3f}")
        print(f"Average citation accuracy: {avg_citation:.3f}")

    skipped_or_failed = len(results) - len(completed)
    if skipped_or_failed:
        print(
            f"\n{skipped_or_failed} case(s) did not complete "
            "(missing files, missing credentials, or a pipeline error). See 'error' above."
        )

    print(
        "\nNote: recall is computed at the source-document level as a placeholder. "
        "Chunk-level gold labels require manual annotation (see report/progress_report.md)."
    )


if __name__ == "__main__":
    main()

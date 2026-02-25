import json
from typing import Any

from regcomply.graph.state import PipelineState
from regcomply.llm import chat_json

_SYSTEM = """You are a regulatory compliance analyst. You receive two versions of a financial regulation: a baseline version and an updated version. Your task is to identify every substantive change between them.

A substantive change is one that alters a legal obligation, threshold, deadline, definition, or scope. Typographical corrections and pure formatting differences are not substantive.

Return a JSON object with a single key "change_items" containing a list of objects. Each object must have:
- "section": the section number or heading where the change occurs
- "change_type": one of "new_requirement", "modified_requirement", "deleted_requirement", "extended_deadline", "new_definition"
- "summary": one sentence describing what changed
- "baseline_text": the relevant excerpt from the baseline (empty string if this is a new requirement)
- "updated_text": the relevant excerpt from the updated version (empty string if deleted)
- "compliance_impact": one of "high", "medium", "low" based on how significantly this affects compliance obligations
"""


def run(state: PipelineState) -> dict[str, Any]:
    baseline = state.get("baseline_text", "")
    updated = state.get("updated_text", "")

    if not baseline.strip() or not updated.strip():
        return {"change_items": []}

    prompt = f"""BASELINE VERSION:
{baseline}

UPDATED VERSION:
{updated}

Identify all substantive changes between the baseline and updated versions."""

    raw = chat_json([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": prompt},
    ])

    try:
        data = json.loads(raw)
        change_items = data.get("change_items", [])
    except (json.JSONDecodeError, KeyError):
        change_items = []

    return {"change_items": change_items}

import json
from typing import Any

from regcomply.graph.state import PipelineState
from regcomply.llm import chat_json

_SYSTEM = """You are a senior regulatory compliance advisor at a financial services firm. You have been given:
1. A list of substantive changes detected in an updated regulation.
2. A set of relevant excerpts from the firm's internal compliance policies.

Your task is to generate specific, actionable policy update recommendations. For each recommendation, you must ground it in both a detected regulatory change and a specific policy excerpt.

Return a JSON object with a single key "recommendations" containing a list of objects. Each object must have:
- "recommendation_id": a short unique identifier (e.g., "REC-001")
- "policy_doc": the policy document that needs updating (use the source_doc_id from the provided chunks)
- "priority": one of "critical", "high", "medium", "low"
- "regulatory_change_ref": the section from the regulation where the change occurred
- "current_policy_text": the verbatim excerpt from the current policy that must change (copy exactly from the chunk text provided)
- "recommended_update": a specific, concrete description of what the policy language should say after the update
- "rationale": one to two sentences explaining why this update is required and the risk of non-compliance
- "supporting_chunk_id": the chunk_id of the policy excerpt that supports this recommendation
"""


def _format_chunks(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        parts.append(
            f"[chunk_id: {c['chunk_id']}] [source: {c['source_doc_id']}]\n{c['text']}"
        )
    return "\n\n---\n\n".join(parts)


def _format_changes(change_items: list[dict]) -> str:
    parts = []
    for item in change_items:
        parts.append(
            f"Section {item.get('section', 'N/A')} | {item.get('change_type', '')} | "
            f"Impact: {item.get('compliance_impact', '')} | {item.get('summary', '')}"
        )
    return "\n".join(parts)


def run(state: PipelineState) -> dict[str, Any]:
    change_items = state.get("change_items", [])
    retrieved_chunks = state.get("retrieved_chunks", [])

    if not change_items or not retrieved_chunks:
        return {"draft_recommendations": [], "citations": []}

    prompt = f"""DETECTED REGULATORY CHANGES:
{_format_changes(change_items)}

RELEVANT POLICY EXCERPTS:
{_format_chunks(retrieved_chunks)}

Generate specific policy update recommendations for each high and critical impact regulatory change, grounded in the provided policy excerpts."""

    raw = chat_json([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": prompt},
    ])

    try:
        data = json.loads(raw)
        recs = data.get("recommendations", [])
    except (json.JSONDecodeError, KeyError):
        recs = []

    citations = []
    chunk_map = {c["chunk_id"]: c for c in retrieved_chunks}
    for rec in recs:
        cid = rec.get("supporting_chunk_id", "")
        if cid and cid in chunk_map:
            chunk = chunk_map[cid]
            citations.append({
                "recommendation_id": rec.get("recommendation_id", ""),
                "chunk_id": cid,
                "source_doc_id": chunk.get("source_doc_id", ""),
                "section_path": chunk.get("section_path", ""),
                "verified": rec.get("current_policy_text", "") in chunk.get("text", ""),
            })

    return {"draft_recommendations": recs, "citations": citations}

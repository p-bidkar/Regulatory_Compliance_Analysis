from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    regulation_id: str
    baseline_text: str
    updated_text: str
    change_items: list[dict[str, Any]]
    retrieved_chunks: list[dict[str, Any]]
    draft_recommendations: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    timings: dict[str, float]

"""Pydantic schemas for validating structured LLM output.

Agents parse LLM responses as JSON, but LLMs occasionally return
malformed, incomplete, or wrongly-typed objects even when the response
is valid JSON. These schemas turn that into an explicit, logged
validation step instead of letting bad items pass through silently as
plain dicts.

Items that fail validation are dropped individually (not the whole
batch) and logged with the reason, so one malformed entry does not
discard an otherwise-good response.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

ChangeType = Literal[
    "new_requirement",
    "modified_requirement",
    "deleted_requirement",
    "extended_deadline",
    "new_definition",
]

ComplianceImpact = Literal["high", "medium", "low"]

Priority = Literal["critical", "high", "medium", "low"]


class ChangeItem(BaseModel):
    section: str = "N/A"
    change_type: ChangeType
    summary: str
    baseline_text: str = ""
    updated_text: str = ""
    compliance_impact: ComplianceImpact


class Recommendation(BaseModel):
    recommendation_id: str
    policy_doc: str = ""
    priority: Priority
    regulatory_change_ref: str = ""
    current_policy_text: str
    recommended_update: str = ""
    rationale: str = ""
    supporting_chunk_id: str = ""


def _validate_each(
    raw_items: list[Any], model: type[BaseModel], kind: str
) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        logger.warning("%s: expected a list, got %s", kind, type(raw_items).__name__)
        return []

    valid: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_items):
        try:
            valid.append(model.model_validate(item).model_dump())
        except ValidationError as exc:
            logger.warning(
                "%s: dropped invalid item at index %d (%s)",
                kind,
                idx,
                "; ".join(e["msg"] for e in exc.errors()),
            )
    return valid


def parse_change_items(raw_items: list[Any]) -> list[dict[str, Any]]:
    return _validate_each(raw_items, ChangeItem, "change_item")


def parse_recommendations(raw_items: list[Any]) -> list[dict[str, Any]]:
    return _validate_each(raw_items, Recommendation, "recommendation")

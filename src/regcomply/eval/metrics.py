"""Evaluation metric functions.

Kept dependency-free and independent of the pipeline so they can be
unit tested in isolation and reused once chunk-level gold labels exist.
"""

from __future__ import annotations


def recall_at_k(retrieved_source_docs: set[str], expected_source_docs: set[str]) -> float:
    """Fraction of expected source documents that appear anywhere in the
    retrieved set (document-level proxy for recall@k until chunk-level
    gold labels are available)."""
    if not expected_source_docs:
        return 1.0
    hits = retrieved_source_docs & expected_source_docs
    return len(hits) / len(expected_source_docs)


def citation_accuracy(citations: list[dict]) -> float:
    """Fraction of generated citations whose verbatim quote was verified
    against its cited source chunk."""
    if not citations:
        return 0.0
    verified = sum(1 for c in citations if c.get("verified"))
    return verified / len(citations)

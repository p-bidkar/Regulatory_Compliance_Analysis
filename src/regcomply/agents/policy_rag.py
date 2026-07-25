import logging
from pathlib import Path
from typing import Any

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from regcomply.graph.state import PipelineState

logger = logging.getLogger(__name__)

_INDEX_DIR = Path(__file__).parent.parent.parent.parent / "chroma_db"
_EMBED_MODEL = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
_TOP_K = 6

_index_cache = None


def _load_index():
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    if not _INDEX_DIR.exists():
        return None
    client = chromadb.PersistentClient(path=str(_INDEX_DIR))
    collection = client.get_or_create_collection("policies")
    store = ChromaVectorStore(chroma_collection=collection)
    _index_cache = VectorStoreIndex.from_vector_store(store, embed_model=_EMBED_MODEL)
    return _index_cache


def _build_queries(change_items: list[dict]) -> list[tuple[int, str]]:
    """Return (change_index, query_text) pairs so retrieval can be attributed
    back to the change that produced it, enabling fair allocation across
    changes instead of a single global top-k cutoff."""
    queries: list[tuple[int, str]] = []
    for idx, item in enumerate(change_items):
        parts = []
        if item.get("summary"):
            parts.append(item["summary"])
        if item.get("updated_text"):
            parts.append(item["updated_text"][:300])
        if parts:
            queries.append((idx, " ".join(parts)))
    if not queries:
        queries = [(0, "regulatory compliance recordkeeping electronic storage")]
    return queries


def _node_to_chunk(node) -> dict[str, Any]:
    chunk_id = node.metadata.get("chunk_id", node.node_id)
    return {
        "chunk_id": chunk_id,
        "source_doc_id": node.metadata.get("source_doc_id", ""),
        "section_path": node.metadata.get("section_path", ""),
        "text": node.get_content(),
        "score": round(float(node.score) if node.score is not None else 0.0, 4),
    }


def run(state: PipelineState) -> dict[str, Any]:
    change_items = state.get("change_items", [])
    index = _load_index()

    if index is None:
        logger.warning(
            "policy_rag: no index at %s; run scripts/build_index.py first",
            _INDEX_DIR,
        )
        return {"retrieved_chunks": []}

    retriever = index.as_retriever(similarity_top_k=_TOP_K)
    queries = _build_queries(change_items)

    # Retrieve candidates per change, keeping the highest-scoring version of
    # any chunk_id that multiple changes happen to retrieve.
    per_change_candidates: list[list[dict[str, Any]]] = []
    best_chunk_by_id: dict[str, dict[str, Any]] = {}

    for _change_idx, query in queries:
        nodes = retriever.retrieve(query)
        candidates = [_node_to_chunk(node) for node in nodes]
        per_change_candidates.append(candidates)
        for chunk in candidates:
            existing = best_chunk_by_id.get(chunk["chunk_id"])
            if existing is None or chunk["score"] > existing["score"]:
                best_chunk_by_id[chunk["chunk_id"]] = chunk

    # Round-robin across changes so a handful of high-scoring duplicates from
    # one change cannot crowd out every other change's evidence within the
    # fixed top-k budget.
    selected_ids: set[str] = set()
    retrieved_chunks: list[dict[str, Any]] = []
    cursors = [0] * len(per_change_candidates)

    progressed = True
    while len(retrieved_chunks) < _TOP_K and progressed:
        progressed = False
        for change_idx, candidates in enumerate(per_change_candidates):
            if len(retrieved_chunks) >= _TOP_K:
                break
            cursor = cursors[change_idx]
            while cursor < len(candidates):
                candidate = candidates[cursor]
                cursor += 1
                if candidate["chunk_id"] in selected_ids:
                    continue
                selected_ids.add(candidate["chunk_id"])
                retrieved_chunks.append(best_chunk_by_id[candidate["chunk_id"]])
                progressed = True
                break
            cursors[change_idx] = cursor

    retrieved_chunks.sort(key=lambda x: x["score"], reverse=True)
    return {"retrieved_chunks": retrieved_chunks[:_TOP_K]}

from pathlib import Path
from typing import Any

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from regcomply.graph.state import PipelineState

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


def _build_queries(change_items: list[dict]) -> list[str]:
    queries = []
    for item in change_items:
        parts = []
        if item.get("summary"):
            parts.append(item["summary"])
        if item.get("updated_text"):
            parts.append(item["updated_text"][:300])
        if parts:
            queries.append(" ".join(parts))
    return queries if queries else ["regulatory compliance recordkeeping electronic storage"]


def run(state: PipelineState) -> dict[str, Any]:
    change_items = state.get("change_items", [])
    index = _load_index()

    if index is None:
        return {"retrieved_chunks": []}

    retriever = index.as_retriever(similarity_top_k=_TOP_K)
    queries = _build_queries(change_items)

    seen_ids: set[str] = set()
    retrieved_chunks: list[dict[str, Any]] = []

    for query in queries:
        nodes = retriever.retrieve(query)
        for node in nodes:
            chunk_id = node.metadata.get("chunk_id", node.node_id)
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
            retrieved_chunks.append({
                "chunk_id": chunk_id,
                "source_doc_id": node.metadata.get("source_doc_id", ""),
                "section_path": node.metadata.get("section_path", ""),
                "text": node.get_content(),
                "score": round(float(node.score) if node.score is not None else 0.0, 4),
            })

    retrieved_chunks.sort(key=lambda x: x["score"], reverse=True)
    return {"retrieved_chunks": retrieved_chunks[:_TOP_K]}

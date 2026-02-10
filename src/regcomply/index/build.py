from pathlib import Path

import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from regcomply.chunking.split import Chunk

_EMBED_MODEL = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")


def build_policy_index(chunks: list[Chunk], persist_dir: str | Path) -> None:
    path = Path(persist_dir)
    path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(path))
    collection = client.get_or_create_collection("policies")
    store = ChromaVectorStore(chroma_collection=collection)
    ctx = StorageContext.from_defaults(vector_store=store)
    documents = [
        Document(
            text=c.text,
            metadata={
                "chunk_id": c.chunk_id,
                "source_doc_id": c.source_doc_id,
                "section_path": c.section_path,
            },
        )
        for c in chunks
    ]
    VectorStoreIndex.from_documents(
        documents,
        storage_context=ctx,
        embed_model=_EMBED_MODEL,
        show_progress=False,
    )

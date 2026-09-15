"""
Thin wrapper around a persistent ChromaDB collection. Kept separate from
embeddings.py so you could later swap Chroma for Qdrant/Pinecone/pgvector
without touching the ingestion or retrieval call sites.
"""
from functools import lru_cache

import chromadb

from app.config import settings
from app.rag.embeddings import embed_texts, embed_query

COLLECTION_NAME = "security_kb"


@lru_cache(maxsize=1)
def get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(chunk_ids: list[str], texts: list[str], sources: list[str]) -> None:
    """Embed and store a batch of knowledge-base chunks."""
    collection = get_collection()
    vectors = embed_texts(texts)
    collection.upsert(
        ids=chunk_ids,
        embeddings=vectors,
        documents=texts,
        metadatas=[{"source": s} for s in sources],
    )


def query(text: str, top_k: int) -> list[dict]:
    """Return the top_k most relevant chunks for a query string."""
    collection = get_collection()
    if collection.count() == 0:
        return []

    vector = embed_query(text)
    results = collection.query(
        query_embeddings=[vector],
        n_results=min(top_k, collection.count()),
    )

    hits = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for chunk_id, doc, meta, dist in zip(ids, docs, metas, distances):
        hits.append({
            "chunk_id": chunk_id,
            "text": doc,
            "source": meta.get("source", "unknown"),
            "distance": dist,
        })
    return hits

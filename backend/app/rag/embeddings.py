"""
Wraps sentence-transformers so the rest of the app doesn't care which
embedding model is used. Runs locally -> no per-call API cost, no data
leaves the machine just to compute a vector.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    # Cached so the (relatively large) model is loaded into memory once
    # per process, not once per request.
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]

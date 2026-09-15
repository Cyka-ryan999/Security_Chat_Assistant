"""
Run this once (and again any time sample_data/ changes) to populate the
vector store:

    cd backend
    python -m app.rag.ingest

It walks sample_data/, splits each file into overlapping chunks, and
upserts them into ChromaDB with a stable id derived from filename + index
(so re-running is idempotent and just overwrites existing chunks).
"""
import glob
import hashlib
import os

from app.rag.vector_store import upsert_chunks

SAMPLE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data")

CHUNK_SIZE = 800       # characters per chunk
CHUNK_OVERLAP = 150    # characters of overlap between consecutive chunks


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c.strip() for c in chunks if c.strip()]


def make_chunk_id(source: str, index: int, text: str) -> str:
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{os.path.basename(source)}::{index}::{h}"


def ingest_directory(directory: str = SAMPLE_DATA_DIR) -> int:
    files = sorted(glob.glob(os.path.join(directory, "**", "*.*"), recursive=True))
    files = [f for f in files if f.endswith((".md", ".txt", ".json"))]

    all_ids, all_texts, all_sources = [], [], []

    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()

        for i, chunk in enumerate(chunk_text(raw)):
            all_ids.append(make_chunk_id(filepath, i, chunk))
            all_texts.append(chunk)
            all_sources.append(os.path.basename(filepath))

    if all_ids:
        upsert_chunks(all_ids, all_texts, all_sources)

    return len(all_ids)


if __name__ == "__main__":
    count = ingest_directory()
    print(f"Ingested {count} chunks from {SAMPLE_DATA_DIR}")

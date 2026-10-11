from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.rag.embeddings import embed_query
from app.rag.vector_store import get_collection
from app.routers import audit, chat

# Create audit_logs table on startup if it doesn't exist yet.
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the embedding model and open the Chroma collection once at
    # startup, so the first question does not pay that cost.
    embed_query("warm up")
    get_collection()
    yield


app = FastAPI(
    title="AI-Based Security Chat Assistant",
    description="Defensive RAG assistant that explains security alerts and logs.",
    version="1.0.0",
    lifespan=lifespan,
)

# Dev-friendly CORS. Restrict allow_origins to your real frontend origin
# before deploying anywhere non-local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(audit.router)


@app.get("/health")
def health():
    return {"status": "ok"}

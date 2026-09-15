from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import audit, chat

# Create audit_logs table on startup if it doesn't exist yet.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Based Security Chat Assistant",
    description="Defensive RAG assistant that explains security alerts and logs.",
    version="1.0.0",
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

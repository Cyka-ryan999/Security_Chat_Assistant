from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client-generated session identifier")
    message: str = Field(..., min_length=1, max_length=8000)
    # Optional raw alert/log text the analyst is asking about. If provided,
    # it's included as extra context alongside retrieved knowledge-base chunks.
    log_context: Optional[str] = Field(default=None, max_length=8000)


class Citation(BaseModel):
    source: str
    chunk_id: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    grounded: bool
    flagged: bool
    flag_reason: str = ""


class AuditLogOut(BaseModel):
    id: str
    created_at: datetime
    session_id: str
    user_message: str
    assistant_response: str
    retrieved_sources: str
    input_flagged: bool
    output_flagged: bool
    grounded: bool
    llm_provider: str
    llm_model: str
    latency_ms: int

    class Config:
        from_attributes = True

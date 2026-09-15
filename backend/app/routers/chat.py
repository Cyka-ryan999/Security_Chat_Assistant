import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit_logger import write_audit_log
from app.config import settings
from app.database import get_db
from app.llm_client import call_llm
from app.models import AuditLog
from app.rag.vector_store import query as vector_query
from app.schemas import ChatRequest, ChatResponse, Citation
from app.validation import check_input, check_output, is_grounded

router = APIRouter(prefix="/chat", tags=["chat"])


def get_conversation_history(
    db: Session,
    session_id: str,
    limit: int = 10,
) -> list[dict]:
    """
    Retrieve previous messages and AI responses from the same chat session.

    The AuditLog table already stores:
    - session_id
    - user_message
    - assistant_response

    Therefore we can reuse it as short-term conversation memory.
    """

    previous_logs = (
        db.query(AuditLog)
        .filter(AuditLog.session_id == session_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )

    # Reverse so the oldest message comes first.
    previous_logs.reverse()

    history = []

    for log in previous_logs:
        history.append(
            {
                "user": log.user_message,
                "assistant": log.assistant_response,
            }
        )

    return history


def build_memory_context(history: list[dict]) -> str:
    """
    Convert previous conversation messages into text that can be
    provided to the LLM.
    """

    if not history:
        return ""

    parts = []

    for item in history:
        parts.append(
            f"USER:\n{item['user']}\n\n"
            f"ASSISTANT:\n{item['assistant']}"
        )

    return "\n\n--- PREVIOUS MESSAGE ---\n\n".join(parts)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    start = time.perf_counter()

    # ---------------------------------------------------------
    # 1. Retrieve previous conversation from the same session
    # ---------------------------------------------------------

    conversation_history = get_conversation_history(
        db=db,
        session_id=request.session_id,
        limit=10,
    )

    memory_context = build_memory_context(conversation_history)

    # ---------------------------------------------------------
    # 2. Input validation
    # ---------------------------------------------------------

    input_flagged, input_reason = check_input(request.message)

    # ---------------------------------------------------------
    # 3. RAG retrieval
    # ---------------------------------------------------------

    retrieved_hits = vector_query(
        request.message,
        top_k=settings.retrieval_top_k,
    )

    grounded = is_grounded(retrieved_hits)

    # ---------------------------------------------------------
    # 4. Generate response
    # ---------------------------------------------------------

    if input_flagged:

        answer = (
            "I can't help with that request. I'm scoped to explaining security "
            "alerts and logs defensively — not producing exploit code, attack "
            "instructions, or bypassing my own instructions. If you have an "
            "alert or log you'd like explained, paste it in and ask again."
        )

        output_flagged, output_reason = False, ""

    else:

        # -----------------------------------------------------
        # Combine previous conversation + current log
        # -----------------------------------------------------

        combined_log_context = ""

        if memory_context:
            combined_log_context += (
                "PREVIOUS CONVERSATION MEMORY:\n"
                f"{memory_context}\n\n"
            )

        if request.log_context:
            combined_log_context += (
                "CURRENT USER-PROVIDED LOG / ALERT:\n"
                f"{request.log_context}"
            )

        if not combined_log_context:
            combined_log_context = None

        # -----------------------------------------------------
        # Send everything to the LLM
        # -----------------------------------------------------

        answer = call_llm(
            request.message,
            combined_log_context,
            retrieved_hits,
        )

        # -----------------------------------------------------
        # 5. Output validation
        # -----------------------------------------------------

        output_flagged, output_reason = check_output(answer)

    latency_ms = int((time.perf_counter() - start) * 1000)

    # ---------------------------------------------------------
    # 6. Audit logging
    # ---------------------------------------------------------

    write_audit_log(
        db,
        session_id=request.session_id,
        user_message=request.message,
        retrieved_hits=retrieved_hits,
        assistant_response=answer,
        input_flagged=input_flagged,
        input_flag_reason=input_reason,
        output_flagged=output_flagged,
        output_flag_reason=output_reason,
        grounded=grounded,
        llm_provider=settings.llm_provider,
        llm_model=(
            settings.anthropic_model
            if settings.llm_provider == "anthropic"
            else settings.openai_model
        ),
        latency_ms=latency_ms,
    )

    # ---------------------------------------------------------
    # 7. Citations
    # ---------------------------------------------------------

    citations = [
        Citation(
            source=h["source"],
            chunk_id=h["chunk_id"],
            snippet=h["text"][:200],
        )
        for h in retrieved_hits
    ]

    # ---------------------------------------------------------
    # 8. Return response
    # ---------------------------------------------------------

    return ChatResponse(
        answer=answer,
        citations=citations,
        grounded=grounded,
        flagged=input_flagged or output_flagged,
        flag_reason=input_reason or output_reason,
    )
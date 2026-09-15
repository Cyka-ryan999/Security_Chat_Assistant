import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit_logger import write_audit_log
from app.config import settings
from app.database import get_db
from app.llm_client import call_llm
from app.rag.vector_store import query as vector_query
from app.schemas import ChatRequest, ChatResponse, Citation
from app.validation import check_input, check_output, is_grounded

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    start = time.perf_counter()

    # 1. Input validation
    input_flagged, input_reason = check_input(request.message)

    # 2. Retrieval (even for flagged input, so the audit trail shows what
    #    would have been retrieved — but we short-circuit before calling
    #    the LLM on clearly abusive input).
    retrieved_hits = vector_query(request.message, top_k=settings.retrieval_top_k)
    grounded = is_grounded(retrieved_hits)

    if input_flagged:
        answer = (
            "I can't help with that request. I'm scoped to explaining security "
            "alerts and logs defensively — not producing exploit code, attack "
            "instructions, or bypassing my own instructions. If you have an "
            "alert or log you'd like explained, paste it in and ask again."
        )
        output_flagged, output_reason = False, ""
    else:
        # 3. Generation, grounded in retrieved context
        answer = call_llm(request.message, request.log_context, retrieved_hits)
        # 4. Output validation
        output_flagged, output_reason = check_output(answer)

    latency_ms = int((time.perf_counter() - start) * 1000)

    # 5. Audit logging — always, regardless of outcome
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
        llm_model=settings.anthropic_model if settings.llm_provider == "anthropic" else settings.openai_model,
        latency_ms=latency_ms,
    )

    citations = [
        Citation(source=h["source"], chunk_id=h["chunk_id"], snippet=h["text"][:200])
        for h in retrieved_hits
    ]

    return ChatResponse(
        answer=answer,
        citations=citations,
        grounded=grounded,
        flagged=input_flagged or output_flagged,
        flag_reason=input_reason or output_reason,
    )

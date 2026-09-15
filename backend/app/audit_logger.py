from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    session_id: str,
    user_message: str,
    retrieved_hits: list[dict],
    assistant_response: str,
    input_flagged: bool,
    input_flag_reason: str,
    output_flagged: bool,
    output_flag_reason: str,
    grounded: bool,
    llm_provider: str,
    llm_model: str,
    latency_ms: int,
) -> AuditLog:
    entry = AuditLog(
        session_id=session_id,
        user_message=user_message,
        retrieved_doc_ids=",".join(h["chunk_id"] for h in retrieved_hits),
        retrieved_sources=",".join(sorted(set(h["source"] for h in retrieved_hits))),
        assistant_response=assistant_response,
        input_flagged=input_flagged,
        input_flag_reason=input_flag_reason,
        output_flagged=output_flagged,
        output_flag_reason=output_flag_reason,
        grounded=grounded,
        llm_provider=llm_provider,
        llm_model=llm_model,
        latency_ms=latency_ms,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

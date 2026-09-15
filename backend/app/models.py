import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer

from app.database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class AuditLog(Base):
    """
    One row per chat turn. This is the compliance/audit trail: what was
    asked, what was retrieved, what the model said, and whether validation
    flagged anything. Never delete rows from this table in production —
    audit logs are meant to be append-only.
    """
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_id)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    session_id = Column(String, index=True)

    user_message = Column(Text, nullable=False)
    retrieved_doc_ids = Column(Text)          # comma-separated chunk ids
    retrieved_sources = Column(Text)          # comma-separated source filenames
    assistant_response = Column(Text, nullable=False)

    # Validation / guardrail outcomes
    input_flagged = Column(Boolean, default=False)
    input_flag_reason = Column(Text, default="")
    output_flagged = Column(Boolean, default=False)
    output_flag_reason = Column(Text, default="")
    grounded = Column(Boolean, default=True)  # False if model answered with no retrieved context

    llm_provider = Column(String, default="")
    llm_model = Column(String, default="")
    latency_ms = Column(Integer, default=0)

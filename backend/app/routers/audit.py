from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


def require_admin_key(x_admin_key: str = Header(default="")):
    """
    Minimal demo auth: a shared secret header. Swap this for real
    authentication (OAuth/session-based admin auth) before any real
    deployment — this is here to demonstrate that audit endpoints must
    not be publicly readable, not as a production auth scheme.
    """
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key header")


@router.get("/logs", response_model=list[AuditLogOut], dependencies=[Depends(require_admin_key)])
def list_logs(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(min(limit, 200))
        .all()
    )
    return logs


@router.get("/logs/flagged", response_model=list[AuditLogOut], dependencies=[Depends(require_admin_key)])
def list_flagged_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = (
        db.query(AuditLog)
        .filter((AuditLog.input_flagged == True) | (AuditLog.output_flagged == True))  # noqa: E712
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    return logs

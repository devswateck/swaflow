from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.audit import service
from app.audit.schemas import AuditLogRead
from app.auth.service import require_module_access
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogRead])
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_module_access("settings")),
    db: Session = Depends(get_db),
) -> list[object]:
    return service.list_audit_logs(db, company_id=current_user.company_id, limit=limit, offset=offset)

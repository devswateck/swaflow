from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.users.models import User


def record_audit(
    db: Session,
    *,
    company_id: UUID,
    action: str,
    entity_type: str,
    summary: str,
    entity_id: UUID | None = None,
    actor_user: User | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        company_id=company_id,
        actor_user_id=actor_user.id if actor_user is not None else None,
        actor_role=actor_user.role if actor_user is not None else "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        metadata_json=metadata or {},
    )
    db.add(log)
    db.flush()
    return log


def list_audit_logs(
    db: Session,
    *,
    company_id: UUID,
    limit: int,
    offset: int,
) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.company_id == company_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )

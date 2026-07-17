import logging
import re
from collections.abc import Mapping
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.users.models import User

logger = logging.getLogger(__name__)

_SENSITIVE_KEY_NAMES = (
    "credential",
    "credentials",
    "password",
    "private_key",
    "secret",
    "secret_token",
    "token",
    "access_token",
    "signature",
    "api_key",
    "client_secret",
)
_SAFE_AUDIT_FLAGS = {
    "credentials_configured",
    "secret_configured",
    "app_secret_configured",
    "signature_algorithm",
    "token_count",
}


def _normalize_key_name(key: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key).lower()


def _is_sensitive_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    normalized = _normalize_key_name(key)
    if normalized in _SAFE_AUDIT_FLAGS:
        return False
    return any(
        re.search(rf"(^|[._-]){re.escape(fragment)}([._-]|$)", normalized) is not None
        for fragment in _SENSITIVE_KEY_NAMES
    )


def _sanitize_metadata_value(value):
    if isinstance(value, Mapping):
        return {
            key: _sanitize_metadata_value(child)
            for key, child in value.items()
            if not _is_sensitive_key(key)
        }
    if isinstance(value, list):
        return [_sanitize_metadata_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_metadata_value(item) for item in value)
    return value


def _normalize_audit_metadata(metadata: dict | None) -> dict:
    return jsonable_encoder(_sanitize_metadata_value(metadata or {}))


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
) -> AuditLog | None:
    log = AuditLog(
        company_id=company_id,
        actor_user_id=actor_user.id if actor_user is not None else None,
        actor_role=actor_user.role if actor_user is not None else "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        metadata_json=_normalize_audit_metadata(metadata),
    )
    db.add(log)
    db.flush()
    return log


def record_audit_best_effort(
    db: Session,
    *,
    company_id: UUID,
    action: str,
    entity_type: str,
    summary: str,
    entity_id: UUID | None = None,
    actor_user: User | None = None,
    metadata: dict | None = None,
    access_scope: str | None = None,
) -> AuditLog | None:
    try:
        bind = db.get_bind()
        if bind is None:
            raise RuntimeError("Database session is not bound")
        with Session(bind=bind, autoflush=False, autocommit=False, expire_on_commit=False) as audit_db:
            log = record_audit(
                audit_db,
                company_id=company_id,
                actor_user=actor_user,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                summary=summary,
                metadata={
                    "access_scope": access_scope,
                    **(metadata or {}),
                }
                if access_scope is not None
                else metadata,
            )
            audit_db.commit()
            audit_db.refresh(log)
            return log
    except Exception:
        logger.exception(
            "Failed to persist audit event",
            extra={
                "company_id": str(company_id),
                "actor_user_id": str(actor_user.id) if actor_user is not None else None,
                "action": action,
                "entity_type": entity_type,
            },
        )
        return None


def record_superadmin_access(
    db: Session,
    *,
    company_id: UUID,
    actor_user: User,
    action: str,
    entity_type: str,
    summary: str,
    entity_id: UUID | None = None,
    metadata: dict | None = None,
    access_scope: str | None = None,
) -> AuditLog:
    safe_metadata = {
        "access_scope": access_scope
        or ("cross_tenant" if actor_user.company_id != company_id else "same_tenant"),
        "actor_company_id": str(actor_user.company_id),
    }
    if metadata:
        safe_metadata.update(metadata)
    try:
        return record_audit_best_effort(
            db,
            company_id=company_id,
            actor_user=actor_user,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            metadata=safe_metadata,
        )
    except Exception:
        logger.exception(
            "Failed to persist superadmin access audit",
            extra={
                "company_id": str(company_id),
                "actor_user_id": str(actor_user.id),
                "action": action,
                "entity_type": entity_type,
            },
        )
        return None


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

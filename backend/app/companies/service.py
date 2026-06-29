import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.companies.models import Company
from app.companies.schemas import CompanyCreate, CompanyUpdate
from app.audit.service import record_audit_best_effort, record_superadmin_access
from app.core.security import hash_password
from app.funnels.service import ensure_welcome_funnel
from app.users.permissions import can_access_module, normalize_module_permissions
from app.users.models import User

COMPANY_BUSINESS_MODES = {"products", "appointments", "mixed"}
logger = logging.getLogger(__name__)


def _audit_company_event(db: Session, **kwargs) -> None:
    try:
        record_audit_best_effort(db, **kwargs)
    except Exception:
        logger.exception(
            "Failed to persist company audit event",
            extra={
                "company_id": str(kwargs.get("company_id")),
                "action": kwargs.get("action"),
                "entity_type": kwargs.get("entity_type"),
            },
        )


def list_companies(
    db: Session,
    *,
    limit: int,
    offset: int,
    actor_user: User | None = None,
) -> list[Company]:
    companies = list(
        db.scalars(select(Company).order_by(Company.created_at.desc()).limit(limit).offset(offset))
    )
    if actor_user is not None and actor_user.role == "superadmin":
        try:
            record_superadmin_access(
                db,
                company_id=actor_user.company_id,
                actor_user=actor_user,
                action="superadmin.list_companies",
                entity_type="company",
                summary="Superadmin listed companies",
                metadata={"limit": limit, "offset": offset, "scope": "all"},
                access_scope="platform_wide",
            )
        except Exception:
            logger.exception(
                "Failed to persist superadmin company listing audit",
                extra={"actor_user_id": str(actor_user.id)},
            )
    return companies


def can_access_company_profile(user: User) -> bool:
    if user.role in {"owner", "admin", "superadmin"}:
        return True
    return user.role in {"agent", "viewer"} and can_access_module(user, "settings")


def require_company_profile_access(user: User) -> None:
    if not can_access_company_profile(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def create_company_with_owner(
    db: Session,
    payload: CompanyCreate,
    *,
    actor_user: User | None = None,
) -> tuple[Company, User]:
    company = Company(name=payload.name)
    db.add(company)
    db.flush()

    try:
        owner = User(
            company_id=company.id,
            name=payload.owner.name,
            email=str(payload.owner.email).lower(),
            password_hash=hash_password(payload.owner.password),
            role="owner",
            module_permissions=normalize_module_permissions(None, role="owner"),
        )
        db.add(owner)
        db.flush()
        ensure_welcome_funnel(db, company_id=company.id, commit=False)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company owner already exists",
        ) from None
    except Exception:
        db.rollback()
        raise

    db.refresh(company)
    db.refresh(owner)
    _audit_company_event(
        db,
        company_id=company.id,
        actor_user=actor_user,
        action="company.created",
        entity_type="company",
        entity_id=company.id,
        summary="Company and owner created",
        metadata={"owner_id": str(owner.id), "owner_email": owner.email},
    )
    return company, owner


def get_company_for_user(
    db: Session,
    *,
    company_id: UUID,
    current_company_id: UUID,
    is_superuser: bool = False,
    actor_user: User | None = None,
) -> Company:
    if not is_superuser and company_id != current_company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    if is_superuser and actor_user is not None and company_id != current_company_id:
        try:
            record_superadmin_access(
                db,
                company_id=company_id,
                actor_user=actor_user,
                action="superadmin.access_company",
                entity_type="company",
                entity_id=company.id,
                summary="Superadmin accessed tenant",
                metadata={"requested_company_id": str(company_id)},
            )
        except Exception:
            logger.exception(
                "Failed to persist superadmin company access audit",
                extra={"actor_user_id": str(actor_user.id), "company_id": str(company_id)},
            )
    return company


def update_company(
    db: Session,
    *,
    company_id: UUID,
    current_company_id: UUID,
    payload: CompanyUpdate,
    is_superuser: bool = False,
    actor_user: User | None = None,
) -> Company:
    company = get_company_for_user(
        db,
        company_id=company_id,
        current_company_id=current_company_id,
        is_superuser=is_superuser,
        actor_user=actor_user,
    )
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "business_mode" and value is not None and value not in COMPANY_BUSINESS_MODES:
            if company.business_mode != value:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid business mode",
                )
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    _audit_company_event(
        db,
        company_id=company.id,
        actor_user=actor_user,
        action="company.updated",
        entity_type="company",
        entity_id=company.id,
        summary="Company profile updated",
        metadata=payload.model_dump(exclude_unset=True),
    )
    return company

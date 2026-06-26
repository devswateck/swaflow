from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.companies.models import Company
from app.companies.schemas import CompanyCreate, CompanyUpdate
from app.audit.service import record_audit
from app.core.security import hash_password
from app.funnels.service import ensure_welcome_funnel
from app.users.permissions import can_access_module, normalize_module_permissions
from app.users.models import User

COMPANY_BUSINESS_MODES = {"products", "appointments", "mixed"}


def list_companies(db: Session, *, limit: int, offset: int) -> list[Company]:
    return list(
        db.scalars(select(Company).order_by(Company.created_at.desc()).limit(limit).offset(offset))
    )


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
        record_audit(
            db,
            company_id=company.id,
            actor_user=actor_user,
            action="company.created",
            entity_type="company",
            entity_id=company.id,
            summary="Company and owner created",
            metadata={"owner_id": str(owner.id), "owner_email": owner.email},
        )
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
    return company, owner


def get_company_for_user(
    db: Session,
    *,
    company_id: UUID,
    current_company_id: UUID,
    is_superuser: bool = False,
) -> Company:
    if not is_superuser and company_id != current_company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
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
    )
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "business_mode" and value is not None and value not in COMPANY_BUSINESS_MODES:
            if company.business_mode != value:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid business mode",
                )
        setattr(company, field, value)
    record_audit(
        db,
        company_id=company.id,
        actor_user=actor_user,
        action="company.updated",
        entity_type="company",
        entity_id=company.id,
        summary="Company profile updated",
        metadata=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(company)
    return company

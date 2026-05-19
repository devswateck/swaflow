from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.companies.models import Company
from app.companies.schemas import CompanyCreate, CompanyUpdate
from app.core.security import hash_password
from app.users.models import User


def create_company_with_owner(db: Session, payload: CompanyCreate) -> tuple[Company, User]:
    company = Company(name=payload.name)
    db.add(company)
    db.flush()

    owner = User(
        company_id=company.id,
        name=payload.owner.name,
        email=str(payload.owner.email).lower(),
        password_hash=hash_password(payload.owner.password),
        role="owner",
    )
    db.add(owner)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company owner already exists",
        ) from None

    db.refresh(company)
    db.refresh(owner)
    return company, owner


def get_company_for_user(db: Session, *, company_id: UUID, current_company_id: UUID) -> Company:
    if company_id != current_company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    company = db.scalar(select(Company).where(Company.id == current_company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


def update_company(
    db: Session,
    *,
    company_id: UUID,
    current_company_id: UUID,
    payload: CompanyUpdate,
) -> Company:
    company = get_company_for_user(db, company_id=company_id, current_company_id=current_company_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.users.models import User
from app.users.schemas import UserCreate, UserPasswordReset, UserUpdate

SUPERADMIN_ROLE = "superadmin"
TENANT_ROLES = {"owner", "admin", "agent", "viewer"}
ALLOWED_ROLES = TENANT_ROLES | {SUPERADMIN_ROLE}


def _validate_role(role: str, *, allow_superadmin: bool = False) -> None:
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role")
    if role == SUPERADMIN_ROLE and not allow_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Swateck superuser can assign superadmin role",
        )


def list_users(db: Session, *, company_id: UUID | None, limit: int, offset: int) -> list[User]:
    statement = select(User)
    if company_id is not None:
        statement = statement.where(User.company_id == company_id)
    statement = statement.order_by(User.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement))


def get_user(db: Session, *, company_id: UUID | None, user_id: UUID) -> User:
    statement = select(User).where(User.id == user_id)
    if company_id is not None:
        statement = statement.where(User.company_id == company_id)
    user = db.scalar(statement)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def create_user(
    db: Session,
    *,
    company_id: UUID,
    payload: UserCreate,
    allow_superadmin: bool = False,
) -> User:
    _validate_role(payload.role, allow_superadmin=allow_superadmin)
    user = User(
        company_id=company_id,
        name=payload.name,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from None
    db.refresh(user)
    return user


def update_user(
    db: Session,
    *,
    company_id: UUID | None,
    user_id: UUID,
    payload: UserUpdate,
    allow_superadmin: bool = False,
) -> User:
    user = get_user(db, company_id=company_id, user_id=user_id)
    data = payload.model_dump(exclude_unset=True)
    if "role" in data:
        _validate_role(data["role"], allow_superadmin=allow_superadmin)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"]).lower()
    if password := data.pop("password", None):
        user.password_hash = hash_password(password)
    for field, value in data.items():
        setattr(user, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from None
    db.refresh(user)
    return user


def reset_user_password(
    db: Session,
    *,
    company_id: UUID | None,
    user_id: UUID,
    payload: UserPasswordReset,
) -> None:
    user = get_user(db, company_id=company_id, user_id=user_id)
    user.password_hash = hash_password(payload.password)
    db.commit()


def deactivate_user(db: Session, *, company_id: UUID | None, user_id: UUID) -> None:
    user = get_user(db, company_id=company_id, user_id=user_id)
    user.status = "inactive"
    db.commit()

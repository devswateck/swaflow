from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate

ALLOWED_ROLES = {"owner", "admin", "agent", "viewer"}


def list_users(db: Session, *, company_id: UUID, limit: int, offset: int) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.company_id == company_id)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


def get_user(db: Session, *, company_id: UUID, user_id: UUID) -> User:
    user = db.scalar(select(User).where(User.company_id == company_id, User.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def create_user(db: Session, *, company_id: UUID, payload: UserCreate) -> User:
    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role")
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


def update_user(db: Session, *, company_id: UUID, user_id: UUID, payload: UserUpdate) -> User:
    user = get_user(db, company_id=company_id, user_id=user_id)
    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role")
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


def deactivate_user(db: Session, *, company_id: UUID, user_id: UUID) -> None:
    user = get_user(db, company_id=company_id, user_id=user_id)
    user.status = "inactive"
    db.commit()


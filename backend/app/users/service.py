from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.companies.models import Company
from app.core.security import hash_password
from app.audit.service import record_audit
from app.users.models import User
from app.users.permissions import normalize_module_permissions
from app.users.schemas import UserCreate, UserPasswordReset, UserUpdate

SUPERADMIN_ROLE = "superadmin"
TENANT_ROLES = {"owner", "admin", "agent", "viewer"}
ALLOWED_ROLES = TENANT_ROLES | {SUPERADMIN_ROLE}
PRIVILEGED_TENANT_ROLES = {"owner", "admin"}


def _validate_role(
    role: str,
    *,
    allow_superadmin: bool = False,
    allow_privileged_tenant_roles: bool = False,
    current_role: str | None = None,
) -> None:
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role")
    if role == SUPERADMIN_ROLE and not allow_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Swateck superuser can assign superadmin role",
        )
    if (
        role in PRIVILEGED_TENANT_ROLES
        and not allow_privileged_tenant_roles
        and current_role not in PRIVILEGED_TENANT_ROLES
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privileged tenant roles are reserved for the bootstrap flow",
        )


def _lock_tenant_scope(db: Session, *, company_id: UUID) -> None:
    statement = select(Company.id).where(Company.id == company_id).with_for_update()
    if db.scalar(statement) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")


def _count_active_privileged_tenant_users(
    db: Session,
    *,
    company_id: UUID,
) -> int:
    statement = select(User.id).where(
        User.company_id == company_id,
        User.status == "active",
        User.role.in_(PRIVILEGED_TENANT_ROLES),
    )
    return len(list(db.scalars(statement)))


def _ensure_privileged_tenant_preserved(
    db: Session,
    *,
    user: User,
    next_role: str,
    next_status: str | None,
) -> None:
    if user.role not in PRIVILEGED_TENANT_ROLES or user.status != "active":
        return
    privileged_after_change = next_role in PRIVILEGED_TENANT_ROLES and next_status == "active"
    if privileged_after_change:
        return
    if _count_active_privileged_tenant_users(db, company_id=user.company_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="At least one active owner or admin must remain on the tenant",
        )


def list_users(db: Session, *, company_id: UUID | None, limit: int, offset: int) -> list[User]:
    statement = select(User)
    if company_id is not None:
        statement = statement.where(User.company_id == company_id)
    statement = statement.order_by(User.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement))


def get_user(db: Session, *, company_id: UUID | None, user_id: UUID, for_update: bool = False) -> User:
    statement = select(User).where(User.id == user_id)
    if company_id is not None:
        statement = statement.where(User.company_id == company_id)
    if for_update:
        statement = statement.with_for_update()
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
    actor_user: User | None = None,
) -> User:
    _validate_role(
        payload.role,
        allow_superadmin=allow_superadmin,
        allow_privileged_tenant_roles=False,
    )
    user = User(
        company_id=company_id,
        name=payload.name,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        module_permissions=normalize_module_permissions(payload.module_permissions, role=payload.role),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from None
    db.refresh(user)
    record_audit(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        summary="User created",
        metadata={"email": user.email, "role": user.role},
    )
    db.commit()
    return user


def update_user(
    db: Session,
    *,
    company_id: UUID | None,
    user_id: UUID,
    payload: UserUpdate,
    allow_superadmin: bool = False,
    actor_user: User | None = None,
) -> User:
    user = get_user(db, company_id=company_id, user_id=user_id)
    _lock_tenant_scope(db, company_id=user.company_id)
    data = payload.model_dump(exclude_unset=True)
    if "role" in data:
        _validate_role(
            data["role"],
            allow_superadmin=allow_superadmin,
            allow_privileged_tenant_roles=False,
            current_role=user.role,
        )
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"]).lower()
    next_role = data.get("role", user.role)
    next_status = data.get("status", user.status)
    _ensure_privileged_tenant_preserved(
        db,
        user=user,
        next_role=next_role,
        next_status=next_status,
    )
    if "module_permissions" in data:
        user.module_permissions = normalize_module_permissions(
            data.pop("module_permissions"),
            role=next_role,
        )
    elif "role" in data:
        user.module_permissions = normalize_module_permissions(None, role=next_role)
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
    record_audit(
        db,
        company_id=user.company_id,
        actor_user=actor_user,
        action="user.updated",
        entity_type="user",
        entity_id=user.id,
        summary="User updated",
        metadata=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    return user


def reset_user_password(
    db: Session,
    *,
    company_id: UUID | None,
    user_id: UUID,
    payload: UserPasswordReset,
    actor_user: User | None = None,
) -> None:
    user = get_user(db, company_id=company_id, user_id=user_id)
    _lock_tenant_scope(db, company_id=user.company_id)
    user.password_hash = hash_password(payload.password)
    record_audit(
        db,
        company_id=user.company_id,
        actor_user=actor_user,
        action="user.password_reset",
        entity_type="user",
        entity_id=user.id,
        summary="User password reset",
    )
    db.commit()


def deactivate_user(
    db: Session,
    *,
    company_id: UUID | None,
    user_id: UUID,
    actor_user: User | None = None,
) -> None:
    user = get_user(db, company_id=company_id, user_id=user_id)
    _lock_tenant_scope(db, company_id=user.company_id)
    _ensure_privileged_tenant_preserved(
        db,
        user=user,
        next_role=user.role,
        next_status="inactive",
    )
    user.status = "inactive"
    record_audit(
        db,
        company_id=user.company_id,
        actor_user=actor_user,
        action="user.deactivated",
        entity_type="user",
        entity_id=user.id,
        summary="User deactivated",
    )
    db.commit()

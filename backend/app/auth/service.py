import logging
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.schemas import PasswordChangeRequest
from app.audit.service import record_audit_best_effort
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.users.permissions import effective_module_permissions, ensure_module_access
from app.users.models import User

bearer_scheme = HTTPBearer(auto_error=False)


SUPERADMIN_ROLE = "superadmin"
logger = logging.getLogger(__name__)


def is_superadmin(user: User) -> bool:
    return user.role == SUPERADMIN_ROLE


def authenticate_user(
    db: Session,
    *,
    company_id: UUID | None = None,
    email: str,
    password: str,
) -> User | None:
    statement = select(User).where(
        User.email == email.lower(),
        User.status == "active",
    )
    if company_id is not None:
        statement = statement.where(User.company_id == company_id)

    for user in db.scalars(statement):
        if verify_password(password, user.password_hash):
            return user
    return None


def build_token(user: User) -> str:
    return create_access_token(subject=user.id, company_id=user.company_id, role=user.role)


def build_current_user_payload(user: User) -> dict[str, object]:
    company = user.company
    return {
        "id": user.id,
        "company_id": user.company_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "module_permissions": effective_module_permissions(user),
        "company_currency": company.currency if company is not None else None,
        "company_timezone": company.timezone if company is not None else None,
        "company_logo_url": company.logo_url if company is not None else None,
        "company_banner_url": company.banner_url if company is not None else None,
        "company_profile_url": company.profile_url if company is not None else None,
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
        user_id = UUID(payload["sub"])
        company_id = UUID(payload["company_id"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.company_id == company_id,
            User.status == "active",
        )
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


def require_roles(*roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if is_superadmin(current_user):
            return current_user
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


def require_module_access(*modules: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if is_superadmin(current_user):
            return current_user
        for module in modules:
            ensure_module_access(current_user, module)
        return current_user

    return dependency


def change_own_password(
    db: Session,
    *,
    user: User,
    payload: PasswordChangeRequest,
    actor_user: User | None = None,
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
    )
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    try:
        record_audit_best_effort(
            db,
            company_id=user.company_id,
            actor_user=actor_user or user,
            action="auth.password_changed",
            entity_type="user",
            entity_id=user.id,
            summary="User password updated",
        )
    except Exception:
        logger.exception(
            "Failed to persist password change audit",
            extra={"company_id": str(user.company_id), "user_id": str(user.id)},
        )

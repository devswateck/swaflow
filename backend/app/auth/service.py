from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, decode_token, verify_password
from app.users.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def authenticate_user(db: Session, *, company_id: UUID, email: str, password: str) -> User | None:
    user = db.scalar(
        select(User).where(
            User.company_id == company_id,
            User.email == email.lower(),
            User.status == "active",
        )
    )
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def build_token(user: User) -> str:
    return create_access_token(subject=user.id, company_id=user.company_id, role=user.role)


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
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


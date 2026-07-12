from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user, is_superadmin, require_roles
from app.core.database import get_db
from app.core.schemas import MessageResponse
from app.users import service
from app.users.models import User
from app.users.schemas import UserCreate, UserPasswordReset, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    company_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> list[User]:
    target_company_id = company_id if is_superadmin(current_user) else current_user.company_id
    return service.list_users(
        db,
        company_id=target_company_id,
        limit=limit,
        offset=offset,
        actor_user=current_user,
    )


@router.get("/tenant", response_model=list[UserRead])
def list_tenant_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[User]:
    return service.list_users(
        db,
        company_id=current_user.company_id,
        limit=limit,
        offset=offset,
        actor_user=current_user,
    )


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> User:
    target_company_id = (
        payload.company_id
        if is_superadmin(current_user) and payload.company_id is not None
        else current_user.company_id
    )
    return service.create_user(
        db,
        company_id=target_company_id,
        payload=payload,
        allow_superadmin=is_superadmin(current_user),
        actor_user=current_user,
    )


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> User:
    company_id = None if is_superadmin(current_user) else current_user.company_id
    return service.get_user(db, company_id=company_id, user_id=user_id, actor_user=current_user)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> User:
    company_id = None if is_superadmin(current_user) else current_user.company_id
    return service.update_user(
        db,
        company_id=company_id,
        user_id=user_id,
        payload=payload,
        allow_superadmin=is_superadmin(current_user),
        actor_user=current_user,
    )


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
def reset_password(
    user_id: UUID,
    payload: UserPasswordReset,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    company_id = None if is_superadmin(current_user) else current_user.company_id
    service.reset_user_password(
        db,
        company_id=company_id,
        user_id=user_id,
        payload=payload,
        actor_user=current_user,
    )
    return MessageResponse(detail="Password reset")


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    company_id = None if is_superadmin(current_user) else current_user.company_id
    service.deactivate_user(db, company_id=company_id, user_id=user_id, actor_user=current_user)
    return MessageResponse(detail="User deactivated")

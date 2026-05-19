from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user, require_roles
from app.core.database import get_db
from app.core.schemas import MessageResponse
from app.users import service
from app.users.models import User
from app.users.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[User]:
    return service.list_users(db, company_id=current_user.company_id, limit=limit, offset=offset)


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> User:
    return service.create_user(db, company_id=current_user.company_id, payload=payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    return service.get_user(db, company_id=current_user.company_id, user_id=user_id)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> User:
    return service.update_user(
        db, company_id=current_user.company_id, user_id=user_id, payload=payload
    )


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service.deactivate_user(db, company_id=current_user.company_id, user_id=user_id)
    return MessageResponse(detail="User deactivated")


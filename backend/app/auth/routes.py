from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.schemas import CurrentUserRead, LoginRequest, PasswordChangeRequest, TokenResponse
from app.auth.service import authenticate_user, build_token, change_own_password, get_current_user
from app.core.database import get_db
from app.core.schemas import MessageResponse
from app.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(
        db,
        company_id=payload.company_id,
        email=payload.email,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return TokenResponse(access_token=build_token(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh(current_user: User = Depends(get_current_user)) -> TokenResponse:
    return TokenResponse(access_token=build_token(current_user))


@router.get("/me", response_model=CurrentUserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/password", response_model=MessageResponse)
def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    change_own_password(db, user=current_user, payload=payload)
    return MessageResponse(detail="Password updated")

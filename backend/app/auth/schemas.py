from uuid import UUID

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.schemas import ORMModel


class LoginRequest(BaseModel):
    company_id: UUID | None = None
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserRead(ORMModel):
    id: UUID
    company_id: UUID
    name: str
    email: EmailStr
    role: str
    status: Literal["active", "inactive"]
    module_permissions: dict[str, bool]
    company_timezone: str | None = None
    company_logo_url: str | None = None
    company_banner_url: str | None = None
    company_profile_url: str | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

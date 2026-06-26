from uuid import UUID

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.schemas import TimestampedRead


class UserCreate(BaseModel):
    company_id: UUID | None = None
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="agent", max_length=50)
    module_permissions: dict[str, bool] | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, max_length=50)
    status: Literal["active", "inactive"] | None = None
    module_permissions: dict[str, bool] | None = None


class UserPasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserRead(TimestampedRead):
    company_id: UUID
    name: str
    email: EmailStr
    role: str
    status: Literal["active", "inactive"]
    module_permissions: dict[str, bool]

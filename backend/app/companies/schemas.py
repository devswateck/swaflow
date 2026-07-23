from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.core.schemas import ORMModel, OwnerCreate, TimestampedRead
from app.users.schemas import UserRead


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    owner: OwnerCreate


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    status: str | None = Field(default=None, max_length=30)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, min_length=1, max_length=50)
    currency: str | None = Field(default=None, min_length=1, max_length=10)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    business_mode: str | None = None
    auto_assign_single_additional_user_chats: bool | None = None
    logo_url: str | None = Field(default=None, min_length=1, max_length=2048)
    banner_url: str | None = Field(default=None, min_length=1, max_length=2048)
    profile_url: str | None = Field(default=None, min_length=1, max_length=2048)


class CompanyRead(TimestampedRead):
    name: str
    status: str
    contact_email: str | None = None
    contact_phone: str | None = None
    currency: str | None = None
    timezone: str | None = None
    business_mode: str | None = None
    auto_assign_single_additional_user_chats: bool = True
    logo_url: str | None = None
    banner_url: str | None = None
    profile_url: str | None = None


class CompanyBootstrapRead(ORMModel):
    company: CompanyRead
    owner: UserRead


class CompanyIdPath(BaseModel):
    id: UUID


CompanyBrandingAsset = str

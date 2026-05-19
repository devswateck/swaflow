from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel, OwnerCreate, TimestampedRead
from app.users.schemas import UserRead


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    owner: OwnerCreate


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    status: str | None = Field(default=None, max_length=30)


class CompanyRead(TimestampedRead):
    name: str
    status: str


class CompanyBootstrapRead(ORMModel):
    company: CompanyRead
    owner: UserRead


class CompanyIdPath(BaseModel):
    id: UUID


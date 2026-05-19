from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.core.schemas import TimestampedRead


class ContactCreate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    phone: str = Field(min_length=5, max_length=50)
    email: EmailStr | None = None
    source: str = Field(default="whatsapp", max_length=50)
    metadata: dict = Field(default_factory=dict)


class ContactUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(default=None, min_length=5, max_length=50)
    email: EmailStr | None = None
    source: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=30)
    metadata: dict | None = None


class ContactRead(TimestampedRead):
    company_id: UUID
    name: str | None
    phone: str
    email: EmailStr | None
    source: str
    status: str
    metadata_json: dict


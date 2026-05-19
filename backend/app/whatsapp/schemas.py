from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import TimestampedRead


class WhatsAppAccountCreate(BaseModel):
    phone_number_id: str = Field(min_length=1, max_length=100)
    business_account_id: str | None = Field(default=None, max_length=100)
    access_token: str = Field(min_length=1)
    verify_token: str = Field(min_length=8, max_length=255)


class WhatsAppAccountRead(TimestampedRead):
    company_id: UUID
    phone_number_id: str
    business_account_id: str | None
    verify_token: str
    status: str


class WhatsAppWebhookResponse(BaseModel):
    processed: int
    skipped: int


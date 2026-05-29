from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.core.schemas import TimestampedRead


class IntegrationCreate(BaseModel):
    type: str = Field(min_length=1, max_length=100)
    credentials: str | None = None
    config: dict = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    credentials: str | None = None
    config: dict | None = None
    status: str | None = Field(default=None, max_length=30)


class IntegrationRead(TimestampedRead):
    company_id: UUID
    type: str
    config: dict
    status: str
    credentials_configured: bool


class OutboundWebhookCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    target_url: HttpUrl
    secret_token: str | None = None
    active: bool = True


class OutboundWebhookUpdate(BaseModel):
    event_type: str | None = Field(default=None, min_length=1, max_length=100)
    target_url: HttpUrl | None = None
    secret_token: str | None = None
    active: bool | None = None


class OutboundWebhookRead(TimestampedRead):
    company_id: UUID
    event_type: str
    target_url: str
    active: bool
    secret_configured: bool

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import TimestampedRead


class AppointmentCreate(BaseModel):
    contact_id: UUID
    conversation_id: UUID | None = None
    assigned_user_id: UUID | None = None
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=480)
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    assigned_user_id: UUID | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=480)
    status: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    external_calendar_event_id: str | None = Field(default=None, max_length=255)


class AppointmentRead(TimestampedRead):
    company_id: UUID
    contact_id: UUID
    conversation_id: UUID | None
    assigned_user_id: UUID | None
    scheduled_at: datetime
    duration_minutes: int
    status: str
    notes: str | None
    external_calendar_event_id: str | None


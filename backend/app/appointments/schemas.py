from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.schemas import AiOperationalScheduleRead
from app.core.schemas import TimestampedRead


class AppointmentCreate(BaseModel):
    contact_id: UUID
    conversation_id: UUID | None = None
    assigned_user_id: UUID | None = None
    scheduled_at: datetime
    duration_minutes: int | None = Field(default=None, ge=15, le=480)
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    assigned_user_id: UUID | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=480)
    status: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class AppointmentAvailabilityRequest(BaseModel):
    preferred_period: Literal["morning", "afternoon"]
    duration_minutes: int | None = Field(default=None, ge=15, le=480)
    horizon_days: int = Field(default=7, ge=1, le=7)
    max_options: Literal[3] = 3
    conversation_id: UUID | None = None


class AppointmentAvailabilityOption(BaseModel):
    scheduled_at: datetime
    ends_at: datetime


class AppointmentAvailabilityRead(BaseModel):
    company_id: UUID
    timezone: str
    preferred_period: Literal["morning", "afternoon"]
    duration_minutes: int
    horizon_days: int
    max_options: int
    calendar_integration_active: bool
    validation_source: Literal["external", "internal", "internal_fallback"]
    validation_error: str | None = None
    options: list[AppointmentAvailabilityOption]


class AppointmentOperationalConfigRead(BaseModel):
    status: Literal["draft", "published"] = "draft"
    version: int = 1
    published_at: str | None = None
    draft: AiOperationalScheduleRead = Field(default_factory=AiOperationalScheduleRead)
    published: AiOperationalScheduleRead = Field(default_factory=AiOperationalScheduleRead)


class AppointmentOperationalConfigUpdate(BaseModel):
    status: Literal["draft", "published"] = "draft"
    version: int = 1
    published_at: str | None = None
    draft: AiOperationalScheduleRead = Field(default_factory=AiOperationalScheduleRead)
    published: AiOperationalScheduleRead = Field(default_factory=AiOperationalScheduleRead)


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
    calendar_sync_status: str | None
    calendar_sync_error: str | None
    calendar_synced_at: datetime | None
    calendar_sync_obsolete_at: datetime | None

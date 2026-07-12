from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel, TimestampedRead
from app.events.schemas import EventRead
from app.messages.schemas import MessageRead


class InboxAvailableProductRead(BaseModel):
    id: UUID
    name: str
    available_units: int


class ConversationCreate(BaseModel):
    contact_id: UUID
    channel: str = Field(default="whatsapp", max_length=50)
    current_step: str | None = Field(default=None, max_length=100)


class ConversationAssign(BaseModel):
    assigned_user_id: UUID | None = None


class ConversationFunnelAssign(BaseModel):
    funnel_id: UUID | None = None
    funnel_step_id: UUID | None = None
    current_step: str | None = Field(default=None, max_length=100)


class ConversationSendMessage(BaseModel):
    content: str = Field(min_length=1)


class ConversationRead(TimestampedRead):
    company_id: UUID
    contact_id: UUID
    channel: str
    status: str
    ai_enabled: bool = True
    assigned_user_id: UUID | None
    funnel_id: UUID | None = None
    funnel_step_id: UUID | None = None
    current_step: str | None
    last_message_at: datetime | None
    unread_count: int = 0
    available_product_count: int = 0


class ConversationListItemRead(ConversationRead):
    contact_name: str | None = None
    contact_phone: str
    funnel_name: str | None = None
    funnel_step_name: str | None = None
    last_message: str | None = None
    last_sender_type: str | None = None


class ConversationDetailRead(ConversationRead):
    contact_name: str | None = None
    contact_phone: str
    funnel_name: str | None = None
    funnel_step_name: str | None = None
    last_message: str | None = None
    last_sender_type: str | None = None
    messages: list[MessageRead] = Field(default_factory=list)
    events: list[EventRead] = Field(default_factory=list)
    available_products_preview: list[InboxAvailableProductRead] = Field(default_factory=list)


class ConversationAppointmentIntentRead(ORMModel):
    conversation_id: UUID
    contact_id: UUID
    contact_name: str | None = None
    contact_phone: str
    assigned_user_id: UUID | None = None
    funnel_id: UUID | None = None
    funnel_name: str | None = None
    funnel_step_id: UUID | None = None
    funnel_step_name: str | None = None
    current_step: str | None = None
    preferred_period: str | None = None
    source: str
    prepared_at: datetime

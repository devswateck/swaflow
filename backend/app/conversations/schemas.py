from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import TimestampedRead
from app.messages.schemas import MessageRead


class ConversationCreate(BaseModel):
    contact_id: UUID
    channel: str = Field(default="whatsapp", max_length=50)
    current_step: str | None = Field(default=None, max_length=100)


class ConversationAssign(BaseModel):
    assigned_user_id: UUID | None = None


class ConversationSendMessage(BaseModel):
    content: str = Field(min_length=1)


class ConversationRead(TimestampedRead):
    company_id: UUID
    contact_id: UUID
    channel: str
    status: str
    assigned_user_id: UUID | None
    current_step: str | None
    last_message_at: datetime | None


class ConversationDetailRead(ConversationRead):
    messages: list[MessageRead] = []


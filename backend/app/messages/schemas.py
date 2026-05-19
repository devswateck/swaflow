from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)
    sender_type: str = Field(default="agent", max_length=50)
    message_type: str = Field(default="text", max_length=50)
    metadata: dict = Field(default_factory=dict)


class MessageRead(ORMModel):
    id: UUID
    company_id: UUID
    conversation_id: UUID
    external_message_id: str | None
    sender_type: str
    content: str | None
    message_type: str
    metadata_json: dict
    created_at: datetime


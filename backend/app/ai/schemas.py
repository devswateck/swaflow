from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import TimestampedRead


class AiAgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    system_prompt: str = Field(min_length=1)
    tone: str | None = Field(default=None, max_length=100)
    rules: dict = Field(default_factory=dict)
    active: bool = True


class AiAgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    system_prompt: str | None = Field(default=None, min_length=1)
    tone: str | None = Field(default=None, max_length=100)
    rules: dict | None = None
    active: bool | None = None


class AiAgentRead(TimestampedRead):
    company_id: UUID
    name: str
    system_prompt: str
    tone: str | None
    rules: dict
    active: bool


class IntentClassifyRequest(BaseModel):
    message: str = Field(min_length=1)


class IntentClassifyResponse(BaseModel):
    intent: str
    confidence: float
    entities: dict


class ProductToolRead(BaseModel):
    id: UUID
    name: str
    price: Decimal
    currency: str
    available: bool


class SearchProductsToolResponse(BaseModel):
    products: list[ProductToolRead]


class CheckStockToolResponse(BaseModel):
    available: bool
    quantity_available: int


class ScheduleAppointmentToolRequest(BaseModel):
    contact_id: UUID
    conversation_id: UUID | None = None
    scheduled_at: datetime
    notes: str | None = None


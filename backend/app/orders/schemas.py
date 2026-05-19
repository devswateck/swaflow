from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel, TimestampedRead


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    contact_id: UUID
    conversation_id: UUID | None = None
    items: list[OrderItemCreate] = Field(min_length=1)
    metadata: dict = Field(default_factory=dict)


class OrderItemRead(ORMModel):
    id: UUID
    company_id: UUID
    order_id: UUID
    product_id: UUID
    quantity: int
    unit_price: Decimal
    total: Decimal


class OrderRead(TimestampedRead):
    company_id: UUID
    contact_id: UUID
    conversation_id: UUID | None
    status: str
    total: Decimal
    currency: str
    payment_provider: str | None
    payment_reference: str | None
    payment_link: str | None
    payment_status: str
    metadata_json: dict
    items: list[OrderItemRead] = []


class PaymentLinkRead(BaseModel):
    payment_link: str
    payment_reference: str


from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel


class InventoryUpdate(BaseModel):
    quantity_available: int = Field(ge=0)
    quantity_reserved: int = Field(default=0, ge=0)


class InventoryAdjustment(BaseModel):
    delta_available: int = 0
    delta_reserved: int = 0


class InventoryRead(ORMModel):
    id: UUID
    company_id: UUID
    product_id: UUID
    quantity_available: int
    quantity_reserved: int
    available_units: int
    updated_at: datetime

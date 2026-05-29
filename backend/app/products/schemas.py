from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import TimestampedRead


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    sku: str | None = Field(default=None, max_length=100)
    price: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="COP", max_length=10)
    whatsapp_catalog_id: str | None = Field(default=None, max_length=100)
    whatsapp_product_retailer_id: str | None = Field(default=None, max_length=200)
    metadata: dict = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    sku: str | None = Field(default=None, max_length=100)
    price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, max_length=10)
    whatsapp_catalog_id: str | None = Field(default=None, max_length=100)
    whatsapp_product_retailer_id: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=30)
    metadata: dict | None = None


class ProductRead(TimestampedRead):
    company_id: UUID
    name: str
    description: str | None
    sku: str | None
    price: Decimal
    currency: str
    whatsapp_catalog_id: str | None
    whatsapp_product_retailer_id: str | None
    status: str
    metadata_json: dict

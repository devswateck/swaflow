from decimal import Decimal

from sqlalchemy import JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class Product(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("company_id", "sku", name="uq_products_company_sku"),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sku: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="COP")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    whatsapp_catalog_id: Mapped[str | None] = mapped_column(String(100))
    whatsapp_product_retailer_id: Mapped[str | None] = mapped_column(String(200))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

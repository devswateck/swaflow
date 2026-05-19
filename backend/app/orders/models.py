from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.core.models import CreatedAtMixin, IdMixin, TenantMixin, TimestampMixin


class Order(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "orders"

    contact_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contacts.id"), nullable=False, index=True
    )
    conversation_id: Mapped[object | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id")
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="COP")
    payment_provider: Mapped[str | None] = mapped_column(String(50))
    payment_reference: Mapped[str | None] = mapped_column(String(150), index=True)
    payment_link: Mapped[str | None] = mapped_column(Text)
    payment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base, IdMixin, TenantMixin, CreatedAtMixin):
    __tablename__ = "order_items"

    order_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True
    )
    product_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")

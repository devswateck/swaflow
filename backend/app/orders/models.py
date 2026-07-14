from decimal import Decimal
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.core.models import CreatedAtMixin, IdMixin, TenantMixin, TimestampMixin


class Order(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("company_id", "idempotency_key", name="uq_orders_company_idempotency_key"),
        Index("ix_orders_company_created_at", "company_id", "created_at"),
        Index("ix_orders_company_status_created_at", "company_id", "status", "created_at"),
        Index("ix_orders_company_conversation_id", "company_id", "conversation_id"),
    )

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
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=lambda: f"direct:{uuid4().hex}",
    )
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base, IdMixin, TenantMixin, CreatedAtMixin):
    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_company_product_order_id", "company_id", "product_id", "order_id"),
    )

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

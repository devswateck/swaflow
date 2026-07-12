from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, UpdatedAtMixin


class Inventory(Base, IdMixin, TenantMixin, UpdatedAtMixin):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("company_id", "product_id", name="uq_inventory_company_product"),)

    product_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    quantity_available: Mapped[int] = mapped_column(nullable=False, default=0)
    quantity_reserved: Mapped[int] = mapped_column(nullable=False, default=0)

    @hybrid_property
    def available_units(self) -> int:
        return self.quantity_available - self.quantity_reserved

    @available_units.expression
    def available_units(cls):
        return cls.quantity_available - cls.quantity_reserved

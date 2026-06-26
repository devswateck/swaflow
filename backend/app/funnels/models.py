from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class SalesFunnel(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "sales_funnels"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_sales_funnels_company_name"),
        UniqueConstraint("company_id", "system_key", name="uq_sales_funnels_company_system_key"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    system_key: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    welcome_message: Mapped[str | None] = mapped_column(Text)
    capture_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assignment_criteria: Mapped[str | None] = mapped_column(Text)

    steps: Mapped[list["SalesFunnelStep"]] = relationship(
        back_populates="funnel",
        cascade="all, delete-orphan",
        order_by="SalesFunnelStep.position.asc()",
    )


class SalesFunnelStep(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "sales_funnel_steps"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "funnel_id", "position", name="uq_sales_funnel_steps_position"
        ),
    )

    funnel_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sales_funnels.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    objectives: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    transition_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    funnel: Mapped["SalesFunnel"] = relationship(back_populates="steps")

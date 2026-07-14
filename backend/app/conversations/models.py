from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class Conversation(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_company_created_at", "company_id", "created_at"),
        Index("ix_conversations_company_last_message_at", "company_id", "last_message_at"),
        Index("ix_conversations_company_assigned_user_status", "company_id", "assigned_user_id", "status"),
        Index("ix_conversations_company_funnel_id_funnel_step_id", "company_id", "funnel_id", "funnel_step_id"),
    )

    contact_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contacts.id"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="whatsapp")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    ai_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    assigned_user_id: Mapped[object | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id")
    )
    funnel_id: Mapped[object | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sales_funnels.id"), index=True
    )
    funnel_step_id: Mapped[object | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sales_funnel_steps.id"), index=True
    )
    current_step: Mapped[str | None] = mapped_column(String(100))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")

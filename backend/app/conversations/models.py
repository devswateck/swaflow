from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class Conversation(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "conversations"

    contact_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contacts.id"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="whatsapp")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
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

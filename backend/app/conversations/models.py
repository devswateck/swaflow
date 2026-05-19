from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
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
    current_step: Mapped[str | None] = mapped_column(String(100))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


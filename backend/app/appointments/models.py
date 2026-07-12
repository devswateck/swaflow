from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class Appointment(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "appointments"

    contact_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contacts.id"), nullable=False, index=True
    )
    conversation_id: Mapped[object | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id")
    )
    assigned_user_id: Mapped[object | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id")
    )
    scheduled_at: Mapped[datetime] = mapped_column(nullable=False)
    duration_minutes: Mapped[int] = mapped_column(nullable=False, default=60)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text)
    external_calendar_event_id: Mapped[str | None] = mapped_column(String(255))
    calendar_sync_status: Mapped[str | None] = mapped_column(String(30))
    calendar_sync_error: Mapped[str | None] = mapped_column(Text)
    calendar_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calendar_sync_obsolete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

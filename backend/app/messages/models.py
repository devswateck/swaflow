from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.core.models import CreatedAtMixin, IdMixin, TenantMixin


class Message(Base, IdMixin, TenantMixin, CreatedAtMixin):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_company_created_at", "company_id", "created_at"),)

    conversation_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True
    )
    external_message_id: Mapped[str | None] = mapped_column(String(150), index=True)
    sender_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
        foreign_keys=[conversation_id],
    )

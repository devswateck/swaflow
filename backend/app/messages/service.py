from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.messages.models import Message


def list_messages(
    db: Session, *, company_id: UUID, conversation_id: UUID, limit: int = 100, offset: int = 0
) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.company_id == company_id, Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
    )


def create_message(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    sender_type: str,
    content: str | None,
    message_type: str = "text",
    external_message_id: str | None = None,
    metadata: dict | None = None,
) -> Message:
    message = Message(
        company_id=company_id,
        conversation_id=conversation_id,
        external_message_id=external_message_id,
        sender_type=sender_type,
        content=content,
        message_type=message_type,
        metadata_json=metadata or {},
    )
    db.add(message)
    db.flush()
    return message


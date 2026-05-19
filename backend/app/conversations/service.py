from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contacts.service import get_contact
from app.conversations.models import Conversation
from app.conversations.schemas import ConversationCreate
from app.messages.models import Message
from app.messages.service import create_message
from app.users.models import User


def list_conversations(
    db: Session,
    *,
    company_id: UUID,
    limit: int,
    offset: int,
    status_filter: str | None = None,
) -> list[Conversation]:
    stmt = select(Conversation).where(Conversation.company_id == company_id)
    if status_filter:
        stmt = stmt.where(Conversation.status == status_filter)
    return list(
        db.scalars(
            stmt.order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


def get_conversation(db: Session, *, company_id: UUID, conversation_id: UUID) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.company_id == company_id,
            Conversation.id == conversation_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


def get_conversation_messages(
    db: Session, *, company_id: UUID, conversation_id: UUID
) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.company_id == company_id, Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
    )


def get_or_create_open_conversation(
    db: Session,
    *,
    company_id: UUID,
    contact_id: UUID,
    channel: str = "whatsapp",
) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.company_id == company_id,
            Conversation.contact_id == contact_id,
            Conversation.channel == channel,
            Conversation.status.in_(["open", "waiting_customer", "waiting_human"]),
        )
    )
    if conversation is not None:
        return conversation
    conversation = Conversation(company_id=company_id, contact_id=contact_id, channel=channel)
    db.add(conversation)
    db.flush()
    return conversation


def create_conversation(
    db: Session, *, company_id: UUID, payload: ConversationCreate
) -> Conversation:
    get_contact(db, company_id=company_id, contact_id=payload.contact_id)
    conversation = Conversation(
        company_id=company_id,
        contact_id=payload.contact_id,
        channel=payload.channel,
        current_step=payload.current_step,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def assign_conversation(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    assigned_user_id: UUID | None,
) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    if assigned_user_id is not None:
        assignee = db.scalar(
            select(User).where(User.company_id == company_id, User.id == assigned_user_id)
        )
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    conversation.assigned_user_id = assigned_user_id
    conversation.status = "waiting_human" if assigned_user_id else "open"
    db.commit()
    db.refresh(conversation)
    return conversation


def close_conversation(db: Session, *, company_id: UUID, conversation_id: UUID) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    conversation.status = "closed"
    db.commit()
    db.refresh(conversation)
    return conversation


def append_message(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    sender_type: str,
    content: str,
    message_type: str = "text",
    external_message_id: str | None = None,
    metadata: dict | None = None,
):
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    message = create_message(
        db,
        company_id=company_id,
        conversation_id=conversation.id,
        sender_type=sender_type,
        content=content,
        message_type=message_type,
        external_message_id=external_message_id,
        metadata=metadata,
    )
    conversation.last_message_at = datetime.now(UTC)
    if sender_type == "customer" and conversation.status == "waiting_customer":
        conversation.status = "open"
    db.commit()
    db.refresh(message)
    return message


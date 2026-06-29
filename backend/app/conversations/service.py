from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contacts.models import Contact
from app.contacts.service import get_contact
from app.audit.service import record_audit_best_effort
from app.conversations.models import Conversation
from app.conversations.schemas import ConversationCreate
from app.funnels.models import SalesFunnel, SalesFunnelStep
from app.funnels.service import ensure_welcome_funnel
from app.messages.models import Message
from app.messages.service import create_message
from app.realtime import realtime_manager
from app.users.models import User


def list_conversations(
    db: Session,
    *,
    company_id: UUID,
    limit: int,
    offset: int,
    status_filter: str | None = None,
    funnel_id: UUID | None = None,
    funnel_step_id: UUID | None = None,
) -> list[Conversation]:
    stmt = select(Conversation).where(Conversation.company_id == company_id)
    if status_filter:
        stmt = stmt.where(Conversation.status == status_filter)
    if funnel_id is not None:
        stmt = stmt.where(Conversation.funnel_id == funnel_id)
    if funnel_step_id is not None:
        stmt = stmt.where(Conversation.funnel_step_id == funnel_step_id)
    return list(
        db.scalars(
            stmt.order_by(
                Conversation.last_message_at.is_(None).asc(),
                Conversation.last_message_at.desc(),
                Conversation.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
    )


def conversation_to_inbox_item(db: Session, *, conversation: Conversation) -> dict:
    contact = db.scalar(
        select(Contact).where(
            Contact.company_id == conversation.company_id,
            Contact.id == conversation.contact_id,
        )
    )
    last_message = db.scalar(
        select(Message)
        .where(
            Message.company_id == conversation.company_id,
            Message.conversation_id == conversation.id,
        )
        .order_by(Message.created_at.desc())
    )
    funnel_name = None
    funnel_step_name = None
    if conversation.funnel_id:
        funnel = db.scalar(
            select(SalesFunnel).where(
                SalesFunnel.company_id == conversation.company_id,
                SalesFunnel.id == conversation.funnel_id,
            )
        )
        funnel_name = funnel.name if funnel else None
    if conversation.funnel_step_id:
        step = db.scalar(
            select(SalesFunnelStep).where(
                SalesFunnelStep.company_id == conversation.company_id,
                SalesFunnelStep.id == conversation.funnel_step_id,
            )
        )
        funnel_step_name = step.name if step else None
    return {
        "id": conversation.id,
        "company_id": conversation.company_id,
        "contact_id": conversation.contact_id,
        "channel": conversation.channel,
        "status": conversation.status,
        "assigned_user_id": conversation.assigned_user_id,
        "funnel_id": conversation.funnel_id,
        "funnel_step_id": conversation.funnel_step_id,
        "current_step": conversation.current_step,
        "funnel_name": funnel_name,
        "funnel_step_name": funnel_step_name,
        "last_message_at": conversation.last_message_at,
        "unread_count": conversation.unread_count,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "contact_name": contact.name if contact else None,
        "contact_phone": contact.phone if contact else "",
        "last_message": last_message.content if last_message else None,
        "last_sender_type": last_message.sender_type if last_message else None,
    }


def get_conversation(db: Session, *, company_id: UUID, conversation_id: UUID) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.company_id == company_id,
            Conversation.id == conversation_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
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


def _apply_default_funnel(
    db: Session, *, company_id: UUID, conversation: Conversation
) -> None:
    if conversation.funnel_id is not None:
        return
    default_funnel = ensure_welcome_funnel(db, company_id=company_id, commit=False)
    default_step = default_funnel.steps[0] if default_funnel.steps else None
    conversation.funnel_id = default_funnel.id
    conversation.funnel_step_id = default_step.id if default_step else None
    if conversation.current_step is None:
        conversation.current_step = default_step.code if default_step else "bienvenida"


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
        if conversation.funnel_id is None:
            _apply_default_funnel(db, company_id=company_id, conversation=conversation)
        return conversation
    conversation = Conversation(company_id=company_id, contact_id=contact_id, channel=channel)
    db.add(conversation)
    db.flush()
    _apply_default_funnel(db, company_id=company_id, conversation=conversation)
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
    db.flush()
    _apply_default_funnel(db, company_id=company_id, conversation=conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def assign_conversation(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    assigned_user_id: UUID | None,
    actor_user: User | None = None,
) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    previous_assigned_user_id = conversation.assigned_user_id
    previous_status = conversation.status
    if assigned_user_id is not None:
        assignee = db.scalar(
            select(User).where(User.company_id == company_id, User.id == assigned_user_id)
        )
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    conversation.assigned_user_id = assigned_user_id
    conversation.status = "waiting_human" if assigned_user_id else "open"
    db.commit()
    db.refresh(conversation)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="conversation.assigned",
        entity_type="conversation",
        entity_id=conversation.id,
        summary="Conversation reassigned",
        metadata={
            "previous_assigned_user_id": str(previous_assigned_user_id)
            if previous_assigned_user_id is not None
            else None,
            "assigned_user_id": str(assigned_user_id) if assigned_user_id is not None else None,
            "previous_status": previous_status,
            "next_status": conversation.status,
        },
    )
    return conversation


def assign_conversation_funnel(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    funnel_id: UUID | None,
    funnel_step_id: UUID | None,
    current_step: str | None,
    actor_user: User | None = None,
) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    if funnel_id is None:
        previous_funnel_id = conversation.funnel_id
        previous_step_id = conversation.funnel_step_id
        previous_current_step = conversation.current_step
        conversation.funnel_id = None
        conversation.funnel_step_id = None
        conversation.current_step = current_step
        db.commit()
        db.refresh(conversation)
        record_audit_best_effort(
            db,
            company_id=company_id,
            actor_user=actor_user,
            action="conversation.funnel_assigned",
            entity_type="conversation",
            entity_id=conversation.id,
            summary="Conversation funnel cleared",
            metadata={
                "previous_funnel_id": str(previous_funnel_id) if previous_funnel_id is not None else None,
                "previous_funnel_step_id": str(previous_step_id) if previous_step_id is not None else None,
                "previous_current_step": previous_current_step,
                "current_step": current_step,
            },
        )
        return conversation

    funnel = db.scalar(
        select(SalesFunnel).where(
            SalesFunnel.company_id == company_id,
            SalesFunnel.id == funnel_id,
        )
    )
    if funnel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel no encontrado")

    step_id_to_set = None
    step_name_to_set = current_step
    if funnel_step_id is not None:
        step = db.scalar(
            select(SalesFunnelStep).where(
                SalesFunnelStep.company_id == company_id,
                SalesFunnelStep.id == funnel_step_id,
                SalesFunnelStep.funnel_id == funnel_id,
            )
        )
        if step is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paso del funnel no encontrado para el funnel seleccionado",
            )
        step_id_to_set = step.id
        if not step_name_to_set:
            step_name_to_set = step.code

    previous_funnel_id = conversation.funnel_id
    previous_step_id = conversation.funnel_step_id
    previous_current_step = conversation.current_step
    conversation.funnel_id = funnel.id
    conversation.funnel_step_id = step_id_to_set
    conversation.current_step = step_name_to_set
    db.commit()
    db.refresh(conversation)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="conversation.funnel_assigned",
        entity_type="conversation",
        entity_id=conversation.id,
        summary="Conversation funnel reassigned",
        metadata={
            "previous_funnel_id": str(previous_funnel_id) if previous_funnel_id is not None else None,
            "previous_funnel_step_id": str(previous_step_id) if previous_step_id is not None else None,
            "previous_current_step": previous_current_step,
            "funnel_id": str(funnel.id),
            "funnel_step_id": str(step_id_to_set) if step_id_to_set is not None else None,
            "current_step": conversation.current_step,
        },
    )
    return conversation


def close_conversation(db: Session, *, company_id: UUID, conversation_id: UUID) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    conversation.status = "closed"
    db.commit()
    db.refresh(conversation)
    return conversation


def mark_conversation_read(
    db: Session, *, company_id: UUID, conversation_id: UUID
) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    conversation.unread_count = 0
    db.commit()
    db.refresh(conversation)
    realtime_manager.publish(
        company_id,
        "conversation.read",
        {
            "conversation_id": str(conversation.id),
            "unread_count": conversation.unread_count,
        },
    )
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
    actor_user: User | None = None,
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
    if sender_type == "customer":
        conversation.unread_count = (conversation.unread_count or 0) + 1
    if sender_type == "customer" and conversation.status == "waiting_customer":
        conversation.status = "open"
    db.commit()
    db.refresh(message)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="message.created",
        entity_type="message",
        entity_id=message.id,
        summary="Message appended to conversation",
        metadata={
            "conversation_id": str(conversation.id),
            "sender_type": sender_type,
            "message_type": message_type,
            "external_message_id": external_message_id,
            "content_length": len(content) if content is not None else 0,
        },
    )
    return message

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.companies.models import Company
from app.contacts.models import Contact
from app.contacts.service import get_contact
from app.audit.service import record_audit_best_effort
from app.conversations.models import Conversation
from app.conversations.schemas import ConversationCreate
from app.events.models import Event
from app.events.service import create_event
from app.events.service import list_conversation_events
from app.funnels.models import SalesFunnel, SalesFunnelStep
from app.funnels.service import ensure_welcome_funnel
from app.inventory.models import Inventory
from app.inventory.service import available_units
from app.messages.models import Message
from app.messages.service import create_message
from app.products.models import Product
from app.realtime import realtime_manager
from app.users.permissions import can_access_module
from app.users.models import User

PRIVILEGED_ASSIGNMENT_ROLES = {"owner", "admin", "superadmin"}
CONVERSATION_INACTIVITY_CLOSE_HOURS = 24


def _conversation_is_expired(conversation: Conversation) -> bool:
    if conversation.status == "closed" or conversation.last_message_at is None:
        return False
    last_message_at = conversation.last_message_at
    if last_message_at.tzinfo is None:
        last_message_at = last_message_at.replace(tzinfo=UTC)
    else:
        last_message_at = last_message_at.astimezone(UTC)
    return datetime.now(UTC) - last_message_at >= timedelta(
        hours=CONVERSATION_INACTIVITY_CLOSE_HOURS
    )


def _close_conversation_for_inactivity(
    db: Session,
    *,
    company_id: UUID,
    conversation: Conversation,
) -> bool:
    if not _conversation_is_expired(conversation):
        return False
    conversation.status = "closed"
    _record_conversation_event(
        db,
        company_id=company_id,
        conversation=conversation,
        event_type="conversation.closed",
        payload={"status": conversation.status, "reason": "inactivity"},
    )
    db.commit()
    db.refresh(conversation)
    realtime_manager.publish(
        company_id,
        "conversation.closed",
        {
            "conversation_id": str(conversation.id),
            "status": conversation.status,
            "reason": "inactivity",
        },
    )
    return True


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
    conversations = list(
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
    filtered_conversations: list[Conversation] = []
    for conversation in conversations:
        was_closed = _close_conversation_for_inactivity(db, company_id=company_id, conversation=conversation)
        if was_closed and status_filter is not None and status_filter != "closed":
            continue
        filtered_conversations.append(conversation)
    return filtered_conversations


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
    available_product_count = _count_available_products(db, company_id=conversation.company_id)
    available_products_preview = _list_available_products_preview(
        db,
        company_id=conversation.company_id,
        limit=3,
    )
    return {
        "id": conversation.id,
        "company_id": conversation.company_id,
        "contact_id": conversation.contact_id,
        "channel": conversation.channel,
        "status": conversation.status,
        "ai_enabled": conversation.ai_enabled,
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
        "available_product_count": available_product_count,
        "available_products_preview": available_products_preview,
    }


def _available_products_stmt(
    *,
    company_id: UUID,
    limit: int | None = None,
):
    stmt = (
        select(Product, Inventory)
        .join(
            Inventory,
            (Inventory.company_id == Product.company_id)
            & (Inventory.product_id == Product.id),
        )
            .where(
                Product.company_id == company_id,
                Product.status == "active",
                Product.whatsapp_catalog_id.is_not(None),
                Product.whatsapp_product_retailer_id.is_not(None),
                Inventory.available_units > 0,
            )
            .order_by(Product.name.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return stmt


def _count_available_products(db: Session, *, company_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count(Product.id))
            .join(
                Inventory,
                (Inventory.company_id == Product.company_id)
                & (Inventory.product_id == Product.id),
            )
            .where(
                Product.company_id == company_id,
                Product.status == "active",
                Product.whatsapp_catalog_id.is_not(None),
                Product.whatsapp_product_retailer_id.is_not(None),
                Inventory.available_units > 0,
            )
        )
        or 0
    )


def _list_available_products_preview(
    db: Session,
    *,
    company_id: UUID,
    limit: int,
) -> list[dict]:
    rows = list(db.execute(_available_products_stmt(company_id=company_id, limit=limit)))
    return [
        {
            "id": product.id,
            "name": product.name,
            "available_units": available_units(inventory),
        }
        for product, inventory in rows
    ]


def get_conversation(db: Session, *, company_id: UUID, conversation_id: UUID) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.company_id == company_id,
            Conversation.id == conversation_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    _close_conversation_for_inactivity(db, company_id=company_id, conversation=conversation)
    return conversation


def _lock_company_scope(db: Session, *, company_id: UUID) -> Company:
    company = db.scalar(
        select(Company)
        .where(Company.id == company_id)
        .with_for_update()
    )
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    db.refresh(company)
    return company


def _lock_conversation_scope(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
) -> Conversation:
    conversation = db.scalar(
        select(Conversation)
        .where(
            Conversation.company_id == company_id,
            Conversation.id == conversation_id,
        )
        .with_for_update()
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversacion no encontrada")
    return conversation


def _build_assignment_payload(
    *,
    conversation: Conversation,
    previous_assigned_user_id: UUID | None,
    assigned_user_id: UUID | None,
    previous_status: str,
    next_status: str,
    assignment_source: str,
) -> dict:
    return {
        "conversation_id": str(conversation.id),
        "previous_assigned_user_id": str(previous_assigned_user_id)
        if previous_assigned_user_id is not None
        else None,
        "assigned_user_id": str(assigned_user_id) if assigned_user_id is not None else None,
        "previous_status": previous_status,
        "next_status": next_status,
        "assignment_source": assignment_source,
    }


def _apply_conversation_assignment(
    db: Session,
    *,
    company_id: UUID,
    conversation: Conversation,
    assigned_user_id: UUID | None,
    actor_user: User | None,
    assignment_source: str,
) -> dict | None:
    previous_assigned_user_id = conversation.assigned_user_id
    previous_status = conversation.status
    next_status = "waiting_human" if assigned_user_id is not None else "open"

    if actor_user is None:
        pass
    elif actor_user.role not in PRIVILEGED_ASSIGNMENT_ROLES:
        if assigned_user_id is None or assigned_user_id != actor_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        if previous_assigned_user_id is not None and previous_assigned_user_id != actor_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
    if assigned_user_id is not None and (
        actor_user is None
        or actor_user.role in PRIVILEGED_ASSIGNMENT_ROLES
        or assigned_user_id == actor_user.id
    ):
        assignee = db.scalar(
            select(User).where(
                User.company_id == company_id,
                User.id == assigned_user_id,
                User.status == "active",
            )
        )
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        if not can_access_module(assignee, "inbox"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    if previous_assigned_user_id == assigned_user_id and previous_status == next_status:
        return None

    conversation.assigned_user_id = assigned_user_id
    conversation.status = next_status
    payload = _build_assignment_payload(
        conversation=conversation,
        previous_assigned_user_id=previous_assigned_user_id,
        assigned_user_id=assigned_user_id,
        previous_status=previous_status,
        next_status=next_status,
        assignment_source=assignment_source,
    )
    _record_conversation_event(
        db,
        company_id=company_id,
        conversation=conversation,
        event_type="conversation.assigned",
        payload=payload,
    )
    return payload


def auto_assign_single_additional_user_chat(
    db: Session,
    *,
    company_id: UUID,
    conversation: Conversation,
) -> dict | None:
    company = _lock_company_scope(db, company_id=company_id)
    if company is None or company.auto_assign_single_additional_user_chats is False:
        return None
    locked_conversation = _lock_conversation_scope(
        db,
        company_id=company_id,
        conversation_id=conversation.id,
    )
    if locked_conversation.assigned_user_id is not None:
        return None
    candidate_users = [
        user
        for user in db.scalars(
            select(User)
            .where(
                User.company_id == company_id,
                User.status == "active",
                User.role.in_({"agent", "viewer"}),
            )
            .with_for_update()
        )
        if can_access_module(user, "inbox")
    ]
    if len(candidate_users) != 1:
        return None
    candidate = candidate_users[0]
    return _apply_conversation_assignment(
        db,
        company_id=company_id,
        conversation=locked_conversation,
        assigned_user_id=candidate.id,
        actor_user=None,
        assignment_source="auto",
    )


def set_conversation_ai_enabled(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    ai_enabled: bool,
    actor_user: User | None = None,
) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    previous_ai_enabled = conversation.ai_enabled
    if previous_ai_enabled == ai_enabled:
        return conversation

    conversation.ai_enabled = ai_enabled
    event_type = "conversation.ai_resumed" if ai_enabled else "conversation.ai_paused"
    _record_conversation_event(
        db,
        company_id=company_id,
        conversation=conversation,
        event_type=event_type,
        payload={
            "previous_ai_enabled": previous_ai_enabled,
            "ai_enabled": ai_enabled,
        },
    )
    db.commit()
    db.refresh(conversation)
    realtime_manager.publish(
        company_id,
        event_type,
        {
            "conversation_id": str(conversation.id),
            "ai_enabled": conversation.ai_enabled,
            "previous_ai_enabled": previous_ai_enabled,
        },
    )
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action=event_type,
        entity_type="conversation",
        entity_id=conversation.id,
        summary="Conversation AI state changed",
        metadata={
            "previous_ai_enabled": previous_ai_enabled,
            "ai_enabled": ai_enabled,
        },
    )
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


def get_conversation_events(
    db: Session, *, company_id: UUID, conversation_id: UUID
) -> list[Event]:
    return list_conversation_events(
        db,
        company_id=company_id,
        conversation_id=conversation_id,
    )


def get_conversation_appointment_intent(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
) -> dict:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    events = [
        event
        for event in list_conversation_events(
            db,
            company_id=company_id,
            conversation_id=conversation_id,
        )
        if event.event_type == "conversation.appointment_intent_prepared"
    ]
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contexto de agenda no encontrado",
        )
    appointment_event = max(
        events,
        key=lambda event: (
            str(event.payload.get("prepared_at") or event.created_at.isoformat()),
            event.created_at.isoformat(),
            str(event.id),
        ),
    )
    prepared_at = str(appointment_event.payload.get("prepared_at") or appointment_event.created_at.isoformat())
    return _build_conversation_appointment_intent_context(
        conversation=conversation,
        payload=appointment_event.payload,
        prepared_at=prepared_at,
        snapshot_version=_conversation_appointment_intent_snapshot_version(
            appointment_event, prepared_at=prepared_at
        ),
    )


def _build_conversation_appointment_intent_context(
    *,
    conversation: Conversation,
    payload: dict,
    prepared_at: str,
    snapshot_version: str,
) -> dict:
    def _string_or_none(value: object) -> str | None:
        return value if isinstance(value, str) else None

    def _string_or_empty(value: object) -> str:
        return value if isinstance(value, str) else ""

    return {
        "conversation_id": conversation.id,
        "contact_id": conversation.contact_id,
        "contact_name": _string_or_none(payload.get("contact_name")),
        "contact_phone": _string_or_empty(payload.get("contact_phone")),
        "assigned_user_id": _string_or_none(payload.get("assigned_user_id")),
        "funnel_id": _string_or_none(payload.get("funnel_id")),
        "funnel_name": _string_or_none(payload.get("funnel_name")),
        "funnel_step_id": _string_or_none(payload.get("funnel_step_id")),
        "funnel_step_name": _string_or_none(payload.get("funnel_step_name")),
        "current_step": _string_or_none(payload.get("current_step")),
        "source": _string_or_none(payload.get("source")) or "inbox",
        "prepared_at": _string_or_none(payload.get("prepared_at")) or prepared_at,
        "snapshot_version": snapshot_version,
    }


def _conversation_appointment_intent_snapshot_version(event: Event, *, prepared_at: str) -> str:
    return f"{prepared_at}|{event.id}"


def _record_conversation_event(
    db: Session,
    *,
    company_id: UUID,
    conversation: Conversation,
    event_type: str,
    payload: dict,
) -> Event:
    return create_event(
        db,
        company_id=company_id,
        event_type=event_type,
        payload={"conversation_id": str(conversation.id), **payload},
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
        if _close_conversation_for_inactivity(db, company_id=company_id, conversation=conversation):
            conversation = None
        else:
            if conversation.funnel_id is None:
                _apply_default_funnel(db, company_id=company_id, conversation=conversation)
            return conversation
    conversation = Conversation(
        company_id=company_id,
        contact_id=contact_id,
        channel=channel,
        ai_enabled=True,
    )
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
        ai_enabled=True,
    )
    db.add(conversation)
    db.flush()
    _apply_default_funnel(db, company_id=company_id, conversation=conversation)
    auto_assignment = auto_assign_single_additional_user_chat(
        db,
        company_id=company_id,
        conversation=conversation,
    )
    db.commit()
    db.refresh(conversation)
    if auto_assignment is not None:
        realtime_manager.publish(company_id, "conversation.assigned", auto_assignment)
        record_audit_best_effort(
            db,
            company_id=company_id,
            actor_user=None,
            action="conversation.assigned",
            entity_type="conversation",
            entity_id=conversation.id,
            summary="Conversation auto-assigned",
            metadata=auto_assignment,
        )
    return conversation


def assign_conversation(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    assigned_user_id: UUID | None,
    actor_user: User | None = None,
) -> Conversation:
    _lock_company_scope(db, company_id=company_id)
    conversation = _lock_conversation_scope(
        db,
        company_id=company_id,
        conversation_id=conversation_id,
    )
    transition = _apply_conversation_assignment(
        db,
        company_id=company_id,
        conversation=conversation,
        assigned_user_id=assigned_user_id,
        actor_user=actor_user,
        assignment_source="manual",
    )
    if transition is None:
        return conversation
    db.commit()
    db.refresh(conversation)
    realtime_manager.publish(
        company_id,
        "conversation.assigned",
        transition,
    )
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="conversation.assigned",
        entity_type="conversation",
        entity_id=conversation.id,
        summary=(
            "Conversation reassigned"
            if transition["previous_assigned_user_id"] is not None
            else "Conversation assigned"
        ),
        metadata=transition,
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
        conversation.last_message_at = datetime.now(UTC)
        _record_conversation_event(
            db,
            company_id=company_id,
            conversation=conversation,
            event_type="conversation.funnel_assigned",
            payload={
                "previous_funnel_id": str(previous_funnel_id) if previous_funnel_id is not None else None,
                "previous_funnel_step_id": str(previous_step_id) if previous_step_id is not None else None,
                "previous_current_step": previous_current_step,
                "current_step": current_step,
                "funnel_id": None,
                "funnel_step_id": None,
            },
        )
        db.commit()
        db.refresh(conversation)
        realtime_manager.publish(
            company_id,
            "conversation.funnel_assigned",
            {
                "conversation_id": str(conversation.id),
                "funnel_id": None,
                "funnel_step_id": None,
                "current_step": conversation.current_step,
            },
        )
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
    conversation.last_message_at = datetime.now(UTC)
    _record_conversation_event(
        db,
        company_id=company_id,
        conversation=conversation,
        event_type="conversation.funnel_assigned",
        payload={
            "previous_funnel_id": str(previous_funnel_id) if previous_funnel_id is not None else None,
            "previous_funnel_step_id": str(previous_step_id) if previous_step_id is not None else None,
            "previous_current_step": previous_current_step,
            "funnel_id": str(funnel.id),
            "funnel_step_id": str(step_id_to_set) if step_id_to_set is not None else None,
            "current_step": conversation.current_step,
        },
    )
    db.commit()
    db.refresh(conversation)
    realtime_manager.publish(
        company_id,
        "conversation.funnel_assigned",
        {
            "conversation_id": str(conversation.id),
            "funnel_id": str(conversation.funnel_id) if conversation.funnel_id is not None else None,
            "funnel_step_id": str(conversation.funnel_step_id)
            if conversation.funnel_step_id is not None
            else None,
            "current_step": conversation.current_step,
        },
    )
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


def prepare_conversation_appointment_intent(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    actor_user: User | None = None,
) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    conversation_item = conversation_to_inbox_item(db, conversation=conversation)
    prepared_at = datetime.now(UTC).isoformat()
    payload = {
        "contact_id": str(conversation.contact_id),
        "contact_name": conversation_item["contact_name"],
        "contact_phone": conversation_item["contact_phone"],
        "assigned_user_id": str(conversation.assigned_user_id)
        if conversation.assigned_user_id is not None
        else None,
        "funnel_id": str(conversation.funnel_id) if conversation.funnel_id is not None else None,
        "funnel_name": conversation_item["funnel_name"],
        "funnel_step_id": str(conversation.funnel_step_id)
        if conversation.funnel_step_id is not None
        else None,
        "funnel_step_name": conversation_item["funnel_step_name"],
        "current_step": conversation.current_step,
        "preferred_period": None,
        "prepared_at": prepared_at,
        "source": "inbox",
    }
    appointment_event = _record_conversation_event(
        db,
        company_id=company_id,
        conversation=conversation,
        event_type="conversation.appointment_intent_prepared",
        payload=payload,
    )
    db.commit()
    db.refresh(conversation)
    realtime_manager.publish(
        company_id,
        "conversation.appointment_intent_prepared",
        {
            "conversation_id": str(conversation.id),
            **payload,
        },
    )
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="conversation.appointment_intent_prepared",
        entity_type="conversation",
        entity_id=conversation.id,
        summary="Conversation appointment intent prepared",
        metadata=payload,
    )
    return _build_conversation_appointment_intent_context(
        conversation=conversation,
        payload=payload,
        prepared_at=prepared_at,
        snapshot_version=_conversation_appointment_intent_snapshot_version(appointment_event, prepared_at=prepared_at),
    )


def close_conversation(db: Session, *, company_id: UUID, conversation_id: UUID) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    conversation.status = "closed"
    _record_conversation_event(
        db,
        company_id=company_id,
        conversation=conversation,
        event_type="conversation.closed",
        payload={"status": conversation.status},
    )
    db.commit()
    db.refresh(conversation)
    realtime_manager.publish(
        company_id,
        "conversation.closed",
        {
            "conversation_id": str(conversation.id),
            "status": conversation.status,
        },
    )
    return conversation


def mark_conversation_read(
    db: Session, *, company_id: UUID, conversation_id: UUID
) -> Conversation:
    conversation = get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    if conversation.unread_count == 0:
        return conversation
    conversation.unread_count = 0
    _record_conversation_event(
        db,
        company_id=company_id,
        conversation=conversation,
        event_type="conversation.read",
        payload={"unread_count": conversation.unread_count},
    )
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

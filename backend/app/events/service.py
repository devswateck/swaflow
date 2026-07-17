from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.dispatcher import dispatch_event
from app.events.models import Event
from app.messages.models import Message

CONVERSATION_EVENT_TYPES = (
    "appointment.calendar_sync_failed",
    "appointment.calendar_synced",
    "appointment.cancelled",
    "appointment.created",
    "appointment.updated",
    "conversation.appointment_intent_prepared",
    "conversation.appointment_preference_selected",
    "conversation.assigned",
    "conversation.ai_paused",
    "conversation.ai_resumed",
    "conversation.closed",
    "conversation.funnel_assigned",
    "conversation.read",
    "message.received",
    "message.sent",
    "message.status",
    "order.cancelled",
    "order.created",
    "order.paid",
    "order.payment_status",
    "order.waiting_payment",
)


def create_event(db: Session, *, company_id: UUID, event_type: str, payload: dict) -> Event:
    event = Event(company_id=company_id, event_type=event_type, payload=payload)
    db.add(event)
    db.flush()
    dispatch_event(db, event)
    return event


def list_events(db: Session, *, company_id: UUID, limit: int, offset: int) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(Event.company_id == company_id)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


def _legacy_status_event_conversation_ids(
    db: Session,
    *,
    company_id: UUID,
    message_id: str,
) -> set[str]:
    message_conversation_ids = {
        str(conversation_id)
        for conversation_id in db.scalars(
            select(Message.conversation_id).where(
                Message.company_id == company_id,
                Message.external_message_id == message_id,
            )
        )
        if conversation_id is not None
    }

    sent_event_conversation_ids = {
        conversation_id
        for conversation_id in db.scalars(
            select(Event.payload["conversation_id"].as_string())
            .where(
                Event.company_id == company_id,
                Event.event_type == "message.sent",
                Event.payload["meta_message_id"].as_string() == message_id,
                Event.payload["conversation_id"].as_string().is_not(None),
            )
        )
        if conversation_id
    }

    if len(message_conversation_ids) == 1:
        return message_conversation_ids

    # If the persisted message rows are ambiguous, let a single sent-event trail
    # rescue the legacy status update instead of dropping a valid conversation.
    if len(message_conversation_ids) > 1:
        if len(sent_event_conversation_ids) == 1:
            return sent_event_conversation_ids
        return set()

    if len(sent_event_conversation_ids) == 1:
        return sent_event_conversation_ids

    return set()


def list_conversation_events(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    limit: int | None = None,
    offset: int = 0,
) -> list[Event]:
    conversation_id_text = str(conversation_id)
    stmt = (
        select(Event)
        .where(
            Event.company_id == company_id,
            Event.event_type.in_(CONVERSATION_EVENT_TYPES),
            Event.payload["conversation_id"].as_string() == conversation_id_text,
        )
        .order_by(Event.created_at.asc(), Event.event_type.asc(), Event.id.asc())
    )
    events = list(db.scalars(stmt))
    seen_event_ids = {event.id for event in events}
    legacy_status_events = list(
        db.scalars(
            select(Event)
            .where(
                Event.company_id == company_id,
                Event.event_type == "message.status",
                Event.payload["conversation_id"].as_string().is_(None),
            )
            .order_by(Event.created_at.asc(), Event.id.asc())
        )
    )
    for event in legacy_status_events:
        payload = event.payload if isinstance(event.payload, dict) else {}
        message_id = payload.get("message_id")
        if not isinstance(message_id, str) or not message_id:
            continue
        if _legacy_status_event_conversation_ids(
            db,
            company_id=company_id,
            message_id=message_id,
        ) != {conversation_id_text}:
            continue
        if event.id not in seen_event_ids:
            seen_event_ids.add(event.id)
            events.append(event)
    events.sort(key=lambda event: (event.created_at, event.event_type, event.id))
    if offset:
        events = events[offset:]
    if limit is not None:
        return events[:limit]
    return events

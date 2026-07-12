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
    status_events = list(
        db.scalars(
            select(Event)
            .join(
                Message,
                (Message.company_id == Event.company_id)
                & (Message.external_message_id == Event.payload["message_id"].as_string()),
            )
            .where(
                Event.company_id == company_id,
                Event.event_type == "message.status",
                Message.conversation_id == conversation_id,
            )
            .order_by(Event.created_at.asc(), Event.id.asc())
        )
    )
    if not status_events:
        if offset:
            events = events[offset:]
        if limit is not None:
            return events[:limit]
        return events
    seen_event_ids = {event.id for event in events}
    for event in status_events:
        if event.id not in seen_event_ids:
            seen_event_ids.add(event.id)
            events.append(event)
    events.sort(key=lambda event: (event.created_at, event.event_type, event.id))
    if offset:
        events = events[offset:]
    if limit is not None:
        return events[:limit]
    return events

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import Event


def create_event(db: Session, *, company_id: UUID, event_type: str, payload: dict) -> Event:
    event = Event(company_id=company_id, event_type=event_type, payload=payload)
    db.add(event)
    db.flush()
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


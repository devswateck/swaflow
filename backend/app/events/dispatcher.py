from sqlalchemy.orm import Session

from app.events.models import Event


def dispatch_event(db: Session, event: Event) -> None:
    """Placeholder for outbound webhooks, email, and n8n auxiliary workflows."""
    event.status = "processed"
    db.flush()


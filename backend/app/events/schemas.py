from datetime import datetime
from uuid import UUID

from app.core.schemas import ORMModel


class EventRead(ORMModel):
    id: UUID
    company_id: UUID
    event_type: str
    payload: dict
    status: str
    created_at: datetime
    processed_at: datetime | None


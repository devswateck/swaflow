from datetime import datetime
from uuid import UUID

from app.core.schemas import ORMModel


class AuditLogRead(ORMModel):
    id: UUID
    company_id: UUID
    actor_user_id: UUID | None
    actor_role: str | None
    action: str
    entity_type: str
    entity_id: UUID | None
    summary: str
    metadata_json: dict
    created_at: datetime
    updated_at: datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.core.database import get_db
from app.events import service
from app.events.models import Event
from app.events.schemas import EventRead
from app.users.models import User

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
def list_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Event]:
    return service.list_events(db, company_id=current_user.company_id, limit=limit, offset=offset)


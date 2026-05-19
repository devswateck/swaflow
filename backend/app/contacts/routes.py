from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.contacts import service
from app.contacts.models import Contact
from app.contacts.schemas import ContactCreate, ContactRead, ContactUpdate
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactRead])
def list_contacts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Contact]:
    return service.list_contacts(db, company_id=current_user.company_id, limit=limit, offset=offset)


@router.post("", response_model=ContactRead, status_code=201)
def create_contact(
    payload: ContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Contact:
    return service.create_contact(db, company_id=current_user.company_id, payload=payload)


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(
    contact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Contact:
    return service.get_contact(db, company_id=current_user.company_id, contact_id=contact_id)


@router.put("/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: UUID,
    payload: ContactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Contact:
    return service.update_contact(
        db, company_id=current_user.company_id, contact_id=contact_id, payload=payload
    )


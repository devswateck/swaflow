from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.contacts.models import Contact
from app.contacts.schemas import ContactCreate, ContactUpdate


def _normalize_phone(phone: str) -> str:
    return "".join(char for char in phone if char.isdigit())


def list_contacts(db: Session, *, company_id: UUID, limit: int, offset: int) -> list[Contact]:
    return list(
        db.scalars(
            select(Contact)
            .where(Contact.company_id == company_id)
            .order_by(Contact.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


def get_contact(db: Session, *, company_id: UUID, contact_id: UUID) -> Contact:
    contact = db.scalar(select(Contact).where(Contact.company_id == company_id, Contact.id == contact_id))
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


def get_or_create_contact(
    db: Session,
    *,
    company_id: UUID,
    phone: str,
    name: str | None = None,
    source: str = "whatsapp",
    metadata: dict | None = None,
) -> Contact:
    normalized_phone = _normalize_phone(phone)
    contact = db.scalar(
        select(Contact).where(
            Contact.company_id == company_id,
            Contact.phone == normalized_phone,
        )
    )
    if contact is not None:
        if name and not contact.name:
            contact.name = name
        return contact
    legacy_phone_expr = func.replace(
        func.replace(
            func.replace(
                func.replace(
                    func.replace(Contact.phone, "+", ""),
                    " ",
                    "",
                ),
                "-",
                "",
            ),
            "(",
            "",
        ),
        ")",
        "",
    )
    contact = db.scalar(
        select(Contact).where(
            Contact.company_id == company_id,
            legacy_phone_expr == normalized_phone,
        )
    )
    if contact is not None:
        if name and not contact.name:
            contact.name = name
        if contact.phone != normalized_phone:
            contact.phone = normalized_phone
        return contact
    contact = Contact(
        company_id=company_id,
        phone=normalized_phone,
        name=name,
        source=source,
        metadata_json=metadata or {},
    )
    db.add(contact)
    db.flush()
    return contact


def create_contact(db: Session, *, company_id: UUID, payload: ContactCreate) -> Contact:
    contact = Contact(
        company_id=company_id,
        name=payload.name,
        phone=_normalize_phone(payload.phone),
        email=str(payload.email).lower() if payload.email else None,
        source=payload.source,
        metadata_json=payload.metadata,
    )
    db.add(contact)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already exists") from None
    db.refresh(contact)
    return contact


def update_contact(
    db: Session, *, company_id: UUID, contact_id: UUID, payload: ContactUpdate
) -> Contact:
    contact = get_contact(db, company_id=company_id, contact_id=contact_id)
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"]).lower()
    if "phone" in data and data["phone"] is not None:
        data["phone"] = _normalize_phone(str(data["phone"]))
    if "metadata" in data:
        data["metadata_json"] = data.pop("metadata")
    for field, value in data.items():
        setattr(contact, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already exists") from None
    db.refresh(contact)
    return contact

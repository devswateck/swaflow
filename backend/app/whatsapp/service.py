from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contacts.service import get_or_create_contact
from app.conversations.service import append_message, get_or_create_open_conversation
from app.core.crypto import encrypt_secret
from app.events.service import create_event
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.schemas import WhatsAppAccountCreate


def create_account(db: Session, *, company_id: UUID, payload: WhatsAppAccountCreate) -> WhatsAppAccount:
    account = WhatsAppAccount(
        company_id=company_id,
        phone_number_id=payload.phone_number_id,
        business_account_id=payload.business_account_id,
        access_token_encrypted=encrypt_secret(payload.access_token),
        verify_token=payload.verify_token,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def list_accounts(db: Session, *, company_id: UUID) -> list[WhatsAppAccount]:
    return list(
        db.scalars(
            select(WhatsAppAccount)
            .where(WhatsAppAccount.company_id == company_id)
            .order_by(WhatsAppAccount.created_at.desc())
        )
    )


def verify_token_exists(db: Session, *, verify_token: str) -> bool:
    return (
        db.scalar(
            select(WhatsAppAccount.id).where(
                WhatsAppAccount.verify_token == verify_token,
                WhatsAppAccount.status == "active",
            )
        )
        is not None
    )


def find_account_by_phone_number_id(
    db: Session, *, phone_number_id: str
) -> WhatsAppAccount | None:
    return db.scalar(
        select(WhatsAppAccount).where(
            WhatsAppAccount.phone_number_id == phone_number_id,
            WhatsAppAccount.status == "active",
        )
    )


def process_webhook_payload(db: Session, *, payload: dict) -> tuple[int, int]:
    processed = 0
    skipped = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            if not phone_number_id:
                skipped += 1
                continue

            account = find_account_by_phone_number_id(db, phone_number_id=phone_number_id)
            if account is None:
                skipped += len(value.get("messages", [])) or 1
                continue

            profile_names = {
                contact.get("wa_id"): contact.get("profile", {}).get("name")
                for contact in value.get("contacts", [])
            }

            for incoming in value.get("messages", []):
                customer_phone = incoming.get("from")
                if not customer_phone:
                    skipped += 1
                    continue
                text_body = incoming.get("text", {}).get("body")
                message_type = incoming.get("type", "text")
                contact = get_or_create_contact(
                    db,
                    company_id=account.company_id,
                    phone=customer_phone,
                    name=profile_names.get(customer_phone),
                    metadata={"whatsapp": {"phone_number_id": phone_number_id}},
                )
                conversation = get_or_create_open_conversation(
                    db,
                    company_id=account.company_id,
                    contact_id=contact.id,
                    channel="whatsapp",
                )
                append_message(
                    db,
                    company_id=account.company_id,
                    conversation_id=conversation.id,
                    sender_type="customer",
                    content=text_body,
                    message_type=message_type,
                    external_message_id=incoming.get("id"),
                    metadata={"raw": incoming, "received_at": datetime.now(UTC).isoformat()},
                )
                create_event(
                    db,
                    company_id=account.company_id,
                    event_type="message.received",
                    payload={
                        "conversation_id": str(conversation.id),
                        "contact_id": str(contact.id),
                        "message_id": incoming.get("id"),
                    },
                )
                db.commit()
                processed += 1

    return processed, skipped


from datetime import UTC, datetime
from decimal import Decimal
import logging
import re
import unicodedata
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.models import AiInteractiveTemplate
from app.ai.runtime import AutoReplyResult, generate_auto_reply
from app.contacts.service import get_or_create_contact
from app.conversations.service import append_message, get_or_create_open_conversation
from app.core.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.events.service import create_event
from app.inventory.models import Inventory
from app.inventory.service import ensure_inventory_for_products
from app.messages.models import Message
from app.products.models import Product
from app.realtime import realtime_manager
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.schemas import (
    WhatsAppAccountCreate,
    WhatsAppAccountTestRead,
    WhatsAppCatalogSyncRequest,
    WhatsAppCatalogSyncResponse,
    WhatsAppSendButtonsRequest,
    WhatsAppSendProductCardsFromDbRequest,
    WhatsAppSendProductCardsRequest,
    WhatsAppSendTextRequest,
    WhatsAppSendTextResponse,
)

GRAPH_API_BASE_URL = "https://graph.facebook.com"
logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    return phone.strip().replace("+", "").replace(" ", "").replace("-", "")


def _normalize_capture_field(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    field = (
        "".join(char for char in normalized if not unicodedata.combining(char))
        .strip()
        .lower()
        .replace(" ", "_")
    )
    aliases = {
        "correo": "email",
        "correo_electronico": "email",
        "e-mail": "email",
        "nombre_completo": "nombre",
        "telefono": "telefono",
        "numero": "numero_de_contacto",
        "numero_contacto": "numero_de_contacto",
        "numero_de_telefono": "numero_de_contacto",
    }
    return aliases.get(field, field)


def _to_decimal_price(value: object) -> Decimal:
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return Decimal("0")
        numeric_match = re.search(r"([0-9]+(?:[.,][0-9]+)?)", text.replace(".", "").replace(",", "."))
        if not numeric_match:
            return Decimal("0")
        try:
            return Decimal(numeric_match.group(1))
        except Exception:
            return Decimal("0")
    if isinstance(value, dict):
        amount = value.get("amount")
        if amount is not None:
            try:
                amount_decimal = Decimal(str(amount))
                offset = value.get("offset")
                if isinstance(offset, int) and offset > 0:
                    return amount_decimal / (Decimal("10") ** offset)
                return amount_decimal
            except Exception:
                return Decimal("0")
    return Decimal("0")


def _meta_request(
    method: str,
    path: str,
    *,
    access_token: str,
    json_body: dict | None = None,
    params: dict | None = None,
) -> dict:
    settings = get_settings()
    url = f"{GRAPH_API_BASE_URL}/{settings.whatsapp_graph_api_version}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {access_token}"}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    try:
        with httpx.Client(timeout=20) as client:
            response = client.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Meta request failed: {exc.__class__.__name__}",
        ) from exc

    data = response.json() if response.content else {}
    if response.status_code >= 400:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        detail = error.get("message") or response.text or "Meta API error"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
    return data if isinstance(data, dict) else {"raw": data}


def _send_text_with_account(
    db: Session,
    *,
    account: WhatsAppAccount,
    to: str,
    body: str,
    source: str = "agent",
) -> WhatsAppSendTextResponse:
    recipient = _normalize_phone(to)
    meta_payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    data = _meta_request(
        "POST",
        f"/{account.phone_number_id}/messages",
        access_token=decrypt_secret(account.access_token_encrypted),
        json_body=meta_payload,
    )
    meta_message_id = None
    if messages := data.get("messages"):
        meta_message_id = messages[0].get("id")

    contact = get_or_create_contact(
        db,
        company_id=account.company_id,
        phone=recipient,
        metadata={"whatsapp": {"phone_number_id": account.phone_number_id}},
    )
    conversation = get_or_create_open_conversation(
        db,
        company_id=account.company_id,
        contact_id=contact.id,
        channel="whatsapp",
    )
    message = append_message(
        db,
        company_id=account.company_id,
        conversation_id=conversation.id,
        sender_type="agent",
        content=body,
        message_type="text",
        external_message_id=meta_message_id,
        metadata={
            "raw": data,
            "sent_at": datetime.now(UTC).isoformat(),
            "source": source,
        },
    )
    create_event(
        db,
        company_id=account.company_id,
        event_type="message.sent",
        payload={
            "conversation_id": str(conversation.id),
            "contact_id": str(contact.id),
            "message_id": str(message.id),
            "meta_message_id": meta_message_id,
            "source": source,
        },
    )
    db.commit()
    realtime_manager.publish(
        account.company_id,
        "message.sent",
        {
            "conversation_id": str(conversation.id),
            "contact_id": str(contact.id),
            "message_id": str(message.id),
            "meta_message_id": meta_message_id,
            "source": source,
        },
    )
    return WhatsAppSendTextResponse(
        ok=True,
        meta_message_id=meta_message_id,
        contact_id=contact.id,
        conversation_id=conversation.id,
        message_id=message.id,
        raw=data,
    )


def _send_interactive_with_account(
    db: Session,
    *,
    account: WhatsAppAccount,
    to: str,
    interactive_payload: dict,
    fallback_text: str,
    source: str,
) -> WhatsAppSendTextResponse:
    recipient = _normalize_phone(to)
    meta_payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "interactive",
        "interactive": interactive_payload,
    }
    data = _meta_request(
        "POST",
        f"/{account.phone_number_id}/messages",
        access_token=decrypt_secret(account.access_token_encrypted),
        json_body=meta_payload,
    )
    meta_message_id = None
    if messages := data.get("messages"):
        meta_message_id = messages[0].get("id")

    contact = get_or_create_contact(
        db,
        company_id=account.company_id,
        phone=recipient,
        metadata={"whatsapp": {"phone_number_id": account.phone_number_id}},
    )
    conversation = get_or_create_open_conversation(
        db,
        company_id=account.company_id,
        contact_id=contact.id,
        channel="whatsapp",
    )
    message = append_message(
        db,
        company_id=account.company_id,
        conversation_id=conversation.id,
        sender_type="agent",
        content=fallback_text,
        message_type="interactive",
        external_message_id=meta_message_id,
        metadata={
            "raw": data,
            "interactive": interactive_payload,
            "sent_at": datetime.now(UTC).isoformat(),
            "source": source,
        },
    )
    create_event(
        db,
        company_id=account.company_id,
        event_type="message.sent",
        payload={
            "conversation_id": str(conversation.id),
            "contact_id": str(contact.id),
            "message_id": str(message.id),
            "meta_message_id": meta_message_id,
            "source": source,
        },
    )
    db.commit()
    realtime_manager.publish(
        account.company_id,
        "message.sent",
        {
            "conversation_id": str(conversation.id),
            "contact_id": str(contact.id),
            "message_id": str(message.id),
            "meta_message_id": meta_message_id,
            "source": source,
        },
    )
    return WhatsAppSendTextResponse(
        ok=True,
        meta_message_id=meta_message_id,
        contact_id=contact.id,
        conversation_id=conversation.id,
        message_id=message.id,
        raw=data,
    )


def _is_duplicate_external_message(
    db: Session, *, company_id: UUID, external_message_id: str | None
) -> bool:
    if not external_message_id:
        return False
    return (
        db.scalar(
            select(Message.id).where(
                Message.company_id == company_id,
                Message.external_message_id == external_message_id,
            )
        )
        is not None
    )


def _incoming_message_content(incoming: dict) -> tuple[str | None, dict | None]:
    message_type = incoming.get("type", "text")
    if message_type == "text":
        return incoming.get("text", {}).get("body"), None

    if message_type == "interactive":
        interactive = incoming.get("interactive", {})
        interactive_type = interactive.get("type")
        reply = interactive.get(interactive_type, {})
        if interactive_type in {"button_reply", "list_reply"} and isinstance(reply, dict):
            reply_id = str(reply.get("id") or "").strip()
            title = str(reply.get("title") or "").strip()
            description = str(reply.get("description") or "").strip()
            return title or description or reply_id or None, {
                "type": interactive_type,
                "id": reply_id or None,
                "title": title or None,
                "description": description or None,
            }

    if message_type == "button":
        button = incoming.get("button", {})
        if isinstance(button, dict):
            text = str(button.get("text") or "").strip()
            payload = str(button.get("payload") or "").strip()
            return text or payload or None, {
                "type": "button",
                "id": payload or None,
                "title": text or None,
            }

    return None, None


def _should_generate_auto_reply(
    *, message_type: str, content: str | None, conversation_status: str
) -> bool:
    return (
        message_type in {"text", "interactive", "button"}
        and bool(content)
        and conversation_status in {"open", "waiting_customer"}
    )


def _send_action_template(
    db: Session,
    *,
    account: WhatsAppAccount,
    to: str,
    action_key: str,
    fallback_text: str,
) -> WhatsAppSendTextResponse | None:
    template = db.scalar(
        select(AiInteractiveTemplate).where(
            AiInteractiveTemplate.company_id == account.company_id,
            AiInteractiveTemplate.action_key == action_key,
            AiInteractiveTemplate.active.is_(True),
        ).order_by(AiInteractiveTemplate.updated_at.desc())
    )
    if template is None:
        return None

    options = template.options if isinstance(template.options, list) else []
    if not options:
        return None

    if template.template_type == "list":
        interactive_payload = {
            "type": "list",
            "body": {"text": template.body_text},
            "action": {
                "button": template.button_text or "Ver opciones",
                "sections": [
                    {
                        "title": template.section_title or "Opciones",
                        "rows": [
                            {
                                "id": str(item.get("id") or ""),
                                "title": str(item.get("title") or "")[:24],
                                "description": str(item.get("description") or "")[:72],
                            }
                            for item in options
                            if str(item.get("id") or "").strip() and str(item.get("title") or "").strip()
                        ],
                    }
                ],
            },
        }
    else:
        interactive_payload = {
            "type": "button",
            "body": {"text": template.body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": str(item.get("id") or "")[:256],
                            "title": str(item.get("title") or "")[:20],
                        },
                    }
                    for item in options[:3]
                    if str(item.get("id") or "").strip() and str(item.get("title") or "").strip()
                ]
            },
        }
    if template.footer_text:
        interactive_payload["footer"] = {"text": template.footer_text}
    response = _send_interactive_with_account(
        db,
        account=account,
        to=to,
        interactive_payload=interactive_payload,
        fallback_text=template.body_text or fallback_text,
        source=f"ai_action:{action_key}",
    )
    sent_message = db.get(Message, response.message_id)
    if sent_message is not None:
        metadata = sent_message.metadata_json if isinstance(sent_message.metadata_json, dict) else {}
        metadata["ai_action"] = {
            "action_key": action_key,
            "template_id": str(template.id),
            "template_name": template.name,
            "template_type": template.template_type,
            "sent_as_interactive": True,
        }
        sent_message.metadata_json = metadata
        db.commit()
    return response


def _action_was_sent(
    db: Session, *, company_id: UUID, conversation_id: UUID, action_key: str
) -> bool:
    messages = db.scalars(
        select(Message).where(
            Message.company_id == company_id,
            Message.conversation_id == conversation_id,
            Message.sender_type == "agent",
        )
    )
    for message in messages:
        metadata = message.metadata_json if isinstance(message.metadata_json, dict) else {}
        if metadata.get("source") == f"ai_action:{action_key}":
            return True
        ai_action = metadata.get("ai_action")
        if isinstance(ai_action, dict) and ai_action.get("action_key") == action_key:
            return True
    return False


def _capture_ai_fields(contact, captured_fields: dict[str, str]) -> dict[str, str]:
    metadata = dict(contact.metadata_json) if isinstance(contact.metadata_json, dict) else {}
    existing = metadata.get("ai_captured_fields")
    merged = (
        {
            _normalize_capture_field(str(key)): str(value).strip()
            for key, value in existing.items()
            if str(key).strip() and str(value).strip()
        }
        if isinstance(existing, dict)
        else {}
    )
    for key, value in captured_fields.items():
        normalized_key = _normalize_capture_field(str(key))
        clean_value = str(value).strip()
        if normalized_key and clean_value:
            merged[normalized_key] = clean_value

    if contact.name:
        merged.setdefault("nombre", contact.name)
    if contact.email:
        merged.setdefault("email", contact.email)
    if contact.phone:
        merged.setdefault("numero_de_contacto", contact.phone)
        merged.setdefault("telefono", contact.phone)

    contact.name = merged.get("nombre") or contact.name
    contact.email = (merged.get("email") or contact.email or "").lower() or None
    metadata["ai_captured_fields"] = merged
    contact.metadata_json = metadata
    return merged


def _resolve_configured_action(
    db: Session,
    *,
    account: WhatsAppAccount,
    conversation,
    contact,
    ai_reply: AutoReplyResult,
) -> str | None:
    captured_fields = _capture_ai_fields(contact, ai_reply.captured_fields)
    db.commit()
    if ai_reply.is_first_contact:
        return None
    if ai_reply.action:
        return ai_reply.action
    if not ai_reply.captured_fields:
        return None

    templates = db.scalars(
        select(AiInteractiveTemplate)
        .where(
            AiInteractiveTemplate.company_id == account.company_id,
            AiInteractiveTemplate.active.is_(True),
            AiInteractiveTemplate.trigger_mode == "after_capture",
        )
        .order_by(AiInteractiveTemplate.updated_at.asc())
    )
    for template in templates:
        required_fields = [
            _normalize_capture_field(str(field))
            for field in (template.trigger_fields or [])
            if str(field).strip()
        ]
        if not required_fields:
            continue
        if not all(captured_fields.get(field) for field in required_fields):
            continue
        if _action_was_sent(
            db,
            company_id=account.company_id,
            conversation_id=conversation.id,
            action_key=template.action_key,
        ):
            continue
        return template.action_key
    return None


def create_account(db: Session, *, company_id: UUID, payload: WhatsAppAccountCreate) -> WhatsAppAccount:
    settings = get_settings()
    verify_token = payload.verify_token or settings.whatsapp_verify_token
    if not verify_token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Verify token is required",
        )
    account = db.scalar(
        select(WhatsAppAccount).where(
            WhatsAppAccount.company_id == company_id,
            WhatsAppAccount.phone_number_id == payload.phone_number_id,
        )
    )
    if account is None:
        account = WhatsAppAccount(company_id=company_id, phone_number_id=payload.phone_number_id)
        db.add(account)
    account.business_account_id = payload.business_account_id
    account.access_token_encrypted = encrypt_secret(payload.access_token)
    account.verify_token = verify_token
    account.status = "active"
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


def get_account(
    db: Session,
    *,
    company_id: UUID,
    account_id: UUID | None = None,
) -> WhatsAppAccount:
    statement = select(WhatsAppAccount).where(
        WhatsAppAccount.company_id == company_id,
        WhatsAppAccount.status == "active",
    )
    if account_id is not None:
        statement = statement.where(WhatsAppAccount.id == account_id)
    else:
        statement = statement.order_by(WhatsAppAccount.created_at.desc())
    account = db.scalar(statement)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WhatsApp account not configured",
        )
    return account


def test_account(db: Session, *, company_id: UUID, account_id: UUID) -> WhatsAppAccountTestRead:
    account = get_account(db, company_id=company_id, account_id=account_id)
    data = _meta_request(
        "GET",
        f"/{account.phone_number_id}",
        access_token=decrypt_secret(account.access_token_encrypted),
        params={"fields": "id,display_phone_number,verified_name,quality_rating"},
    )
    return WhatsAppAccountTestRead(
        ok=True,
        phone_number_id=str(data.get("id") or account.phone_number_id),
        display_phone_number=data.get("display_phone_number"),
        verified_name=data.get("verified_name"),
        quality_rating=data.get("quality_rating"),
        raw=data,
    )


def send_text_message(
    db: Session,
    *,
    company_id: UUID,
    payload: WhatsAppSendTextRequest,
) -> WhatsAppSendTextResponse:
    account = get_account(db, company_id=company_id, account_id=payload.account_id)
    return _send_text_with_account(
        db,
        account=account,
        to=payload.to,
        body=payload.body,
        source="agent_manual",
    )


def send_buttons_message(
    db: Session,
    *,
    company_id: UUID,
    payload: WhatsAppSendButtonsRequest,
) -> WhatsAppSendTextResponse:
    account = get_account(db, company_id=company_id, account_id=payload.account_id)
    interactive_payload = {
        "type": "button",
        "body": {"text": payload.body},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": button.id, "title": button.title}}
                for button in payload.buttons
            ]
        },
    }
    if payload.footer:
        interactive_payload["footer"] = {"text": payload.footer}
    return _send_interactive_with_account(
        db,
        account=account,
        to=payload.to,
        interactive_payload=interactive_payload,
        fallback_text=payload.body,
        source="agent_manual_buttons",
    )


def send_product_cards_message(
    db: Session,
    *,
    company_id: UUID,
    payload: WhatsAppSendProductCardsRequest,
) -> WhatsAppSendTextResponse:
    account = get_account(db, company_id=company_id, account_id=payload.account_id)
    if len(payload.items) == 1:
        interactive_payload = {
            "type": "product",
            "body": {"text": payload.body},
            "action": {
                "catalog_id": payload.catalog_id,
                "product_retailer_id": payload.items[0].product_retailer_id,
            },
        }
    else:
        interactive_payload = {
            "type": "product_list",
            "header": {"type": "text", "text": "Productos recomendados"},
            "body": {"text": payload.body},
            "action": {
                "catalog_id": payload.catalog_id,
                "sections": [
                    {
                        "title": payload.section_title,
                        "product_items": [
                            {"product_retailer_id": item.product_retailer_id}
                            for item in payload.items
                        ],
                    }
                ],
            },
        }
    return _send_interactive_with_account(
        db,
        account=account,
        to=payload.to,
        interactive_payload=interactive_payload,
        fallback_text=payload.body,
        source="agent_manual_product_cards",
    )


def send_product_cards_from_db(
    db: Session,
    *,
    company_id: UUID,
    payload: WhatsAppSendProductCardsFromDbRequest,
) -> WhatsAppSendTextResponse:
    account = get_account(db, company_id=company_id, account_id=payload.account_id)
    products = list(
        db.scalars(
            select(Product).where(
                Product.company_id == company_id,
                Product.id.in_(payload.product_ids),
                Product.status == "active",
            )
        )
    )
    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active products found for selected ids",
        )
    products_by_id = {product.id: product for product in products}
    products = [
        products_by_id[product_id]
        for product_id in payload.product_ids
        if product_id in products_by_id
    ]
    missing_mapping = [
        product.name
        for product in products
        if not product.whatsapp_catalog_id or not product.whatsapp_product_retailer_id
    ]
    if missing_mapping:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Products without WhatsApp mapping: {', '.join(missing_mapping[:3])}",
        )
    catalog_ids = {product.whatsapp_catalog_id for product in products if product.whatsapp_catalog_id}
    if len(catalog_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="All selected products must belong to the same WhatsApp catalog_id",
        )
    catalog_id = next(iter(catalog_ids))
    items = [
        {"product_retailer_id": product.whatsapp_product_retailer_id}
        for product in products
        if product.whatsapp_product_retailer_id
    ]
    if len(items) == 1:
        interactive_payload = {
            "type": "product",
            "body": {"text": payload.body},
            "action": {
                "catalog_id": catalog_id,
                "product_retailer_id": items[0]["product_retailer_id"],
            },
        }
    else:
        interactive_payload = {
            "type": "product_list",
            "header": {"type": "text", "text": "Productos recomendados"},
            "body": {"text": payload.body},
            "action": {
                "catalog_id": catalog_id,
                "sections": [
                    {
                        "title": payload.section_title,
                        "product_items": items,
                    }
                ],
            },
        }
    return _send_interactive_with_account(
        db,
        account=account,
        to=payload.to,
        interactive_payload=interactive_payload,
        fallback_text=payload.body,
        source="agent_product_cards_db",
    )


def _resolve_available_product_ids(
    db: Session,
    *,
    company_id: UUID,
    retailer_ids: list[str],
) -> list[UUID]:
    normalized_ids = list(
        dict.fromkeys(
            str(retailer_id).strip()
            for retailer_id in retailer_ids
            if str(retailer_id).strip()
        )
    )[:10]
    if not normalized_ids:
        return []

    rows = list(
        db.execute(
            select(Product, Inventory)
            .join(
                Inventory,
                (Inventory.company_id == Product.company_id)
                & (Inventory.product_id == Product.id),
            )
            .where(
                Product.company_id == company_id,
                Product.status == "active",
                Product.whatsapp_catalog_id.is_not(None),
                Product.whatsapp_product_retailer_id.in_(normalized_ids),
            )
        )
    )
    product_ids_by_retailer_id = {
        product.whatsapp_product_retailer_id: product.id
        for product, inventory in rows
        if product.whatsapp_product_retailer_id
        and inventory.quantity_available - inventory.quantity_reserved > 0
    }
    return [
        product_ids_by_retailer_id[retailer_id]
        for retailer_id in normalized_ids
        if retailer_id in product_ids_by_retailer_id
    ]


def _list_available_product_ids(
    db: Session,
    *,
    company_id: UUID,
    limit: int = 10,
) -> list[UUID]:
    rows = list(
        db.execute(
            select(Product, Inventory)
            .join(
                Inventory,
                (Inventory.company_id == Product.company_id)
                & (Inventory.product_id == Product.id),
            )
            .where(
                Product.company_id == company_id,
                Product.status == "active",
                Product.whatsapp_catalog_id.is_not(None),
                Product.whatsapp_product_retailer_id.is_not(None),
                Inventory.quantity_available > Inventory.quantity_reserved,
            )
            .order_by(Product.name.asc())
            .limit(limit)
        )
    )
    return [product.id for product, _inventory in rows]


def _interactive_reply_requests_catalog(interactive_reply: dict | None) -> bool:
    if not isinstance(interactive_reply, dict):
        return False
    title = str(interactive_reply.get("title") or "")
    normalized = (
        "".join(
            char
            for char in unicodedata.normalize("NFKD", title)
            if not unicodedata.combining(char)
        )
        .strip()
        .lower()
    )
    return "producto" in normalized or "catalogo" in normalized


def sync_catalog_products(
    db: Session,
    *,
    company_id: UUID,
    payload: WhatsAppCatalogSyncRequest,
) -> WhatsAppCatalogSyncResponse:
    account = get_account(db, company_id=company_id, account_id=payload.account_id)
    try:
        data = _meta_request(
            "GET",
            f"/{payload.catalog_id}/products",
            access_token=decrypt_secret(account.access_token_encrypted),
            params={"fields": "retailer_id,name,description,price,currency,availability"},
        )
    except HTTPException as exc:
        detail = str(exc.detail or "")
        if "nonexisting field (products)" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "El ID ingresado no corresponde a un catalogo de Meta. "
                    "Parece un ID de conjunto (por ejemplo 'All Products'). "
                    "En SwaFlow debes usar el ID del catalogo, no el ID del conjunto."
                ),
            ) from None
        raise
    rows = data.get("data", []) if isinstance(data, dict) else []
    if not isinstance(rows, list):
        rows = []

    created = 0
    updated = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        retailer_id = str(row.get("retailer_id") or "").strip()
        name = str(row.get("name") or "").strip()
        if not retailer_id or not name:
            continue
        existing = db.scalar(
            select(Product).where(
                Product.company_id == company_id,
                Product.whatsapp_product_retailer_id == retailer_id,
            )
        )
        description = str(row.get("description") or "").strip() or None
        currency = str(row.get("currency") or "COP").strip() or "COP"
        availability = str(row.get("availability") or "").lower()
        status = "inactive" if availability in {"out of stock", "discontinued"} else "active"
        price = _to_decimal_price(row.get("price"))
        if price <= 0:
            price = Decimal("1")

        if existing is None:
            db.add(
                Product(
                    company_id=company_id,
                    name=name,
                    description=description,
                    sku=None,
                    price=price,
                    currency=currency,
                    status=status,
                    whatsapp_catalog_id=payload.catalog_id,
                    whatsapp_product_retailer_id=retailer_id,
                    metadata_json={"source": "meta_catalog_sync"},
                )
            )
            created += 1
        else:
            existing.name = name
            existing.description = description
            existing.price = price
            existing.currency = currency
            existing.status = status
            existing.whatsapp_catalog_id = payload.catalog_id
            meta = existing.metadata_json if isinstance(existing.metadata_json, dict) else {}
            meta["source"] = "meta_catalog_sync"
            existing.metadata_json = meta
            updated += 1
    ensure_inventory_for_products(db, company_id=company_id)
    db.commit()
    return WhatsAppCatalogSyncResponse(fetched=len(rows), created=created, updated=updated)


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
                external_message_id = incoming.get("id")
                if _is_duplicate_external_message(
                    db,
                    company_id=account.company_id,
                    external_message_id=external_message_id,
                ):
                    skipped += 1
                    continue
                message_type = incoming.get("type", "text")
                message_content, interactive_reply = _incoming_message_content(incoming)
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
                message = append_message(
                    db,
                    company_id=account.company_id,
                    conversation_id=conversation.id,
                    sender_type="customer",
                    content=message_content,
                    message_type=message_type,
                    external_message_id=external_message_id,
                    metadata={
                        "raw": incoming,
                        "received_at": datetime.now(UTC).isoformat(),
                        **({"interactive_reply": interactive_reply} if interactive_reply else {}),
                    },
                )
                create_event(
                    db,
                    company_id=account.company_id,
                    event_type="message.received",
                    payload={
                        "conversation_id": str(conversation.id),
                        "contact_id": str(contact.id),
                        "message_id": external_message_id,
                    },
                )
                db.commit()
                realtime_manager.publish(
                    account.company_id,
                    "message.received",
                    {
                        "conversation_id": str(conversation.id),
                        "contact_id": str(contact.id),
                        "message_id": str(message.id),
                        "external_message_id": external_message_id,
                        "unread_count": conversation.unread_count,
                    },
                )
                if _should_generate_auto_reply(
                    message_type=message_type,
                    content=message_content,
                    conversation_status=conversation.status,
                ):
                    ai_reply = generate_auto_reply(
                        db,
                        company_id=account.company_id,
                        conversation=conversation,
                        incoming_text=message_content,
                        incoming_interactive_reply=interactive_reply,
                    )
                    if ai_reply:
                        product_cards_sent = False
                        action_sent = False
                        if isinstance(ai_reply, AutoReplyResult):
                            ai_reply.action = _resolve_configured_action(
                                db,
                                account=account,
                                conversation=conversation,
                                contact=contact,
                                ai_reply=ai_reply,
                            )
                            product_ids = _resolve_available_product_ids(
                                db,
                                company_id=account.company_id,
                                retailer_ids=ai_reply.product_retailer_ids,
                            )
                            if (
                                not product_ids
                                and _interactive_reply_requests_catalog(interactive_reply)
                            ):
                                product_ids = _list_available_product_ids(
                                    db,
                                    company_id=account.company_id,
                                )
                            if product_ids:
                                try:
                                    send_product_cards_from_db(
                                        db,
                                        company_id=account.company_id,
                                        payload=WhatsAppSendProductCardsFromDbRequest(
                                            to=customer_phone,
                                            body=ai_reply.reply_text[:1024],
                                            product_ids=product_ids,
                                            account_id=account.id,
                                        ),
                                    )
                                    product_cards_sent = True
                                except HTTPException as exc:
                                    logger.warning(
                                        "AI product cards skipped company_id=%s detail=%s",
                                        account.company_id,
                                        exc.detail,
                                    )
                        if (
                            not product_cards_sent
                            and isinstance(ai_reply, AutoReplyResult)
                            and ai_reply.action
                        ):
                            action_sent = (
                                _send_action_template(
                                    db,
                                    account=account,
                                    to=customer_phone,
                                    action_key=ai_reply.action,
                                    fallback_text=ai_reply.reply_text,
                                )
                                is not None
                            )
                        if not product_cards_sent and not action_sent:
                            body = ai_reply.reply_text if isinstance(ai_reply, AutoReplyResult) else str(ai_reply)
                            response = _send_text_with_account(
                                db,
                                account=account,
                                to=customer_phone,
                                body=body,
                                source="ai_auto_reply",
                            )
                            if isinstance(ai_reply, AutoReplyResult):
                                sent_message = db.get(Message, response.message_id)
                                if sent_message is not None:
                                    metadata = (
                                        sent_message.metadata_json
                                        if isinstance(sent_message.metadata_json, dict)
                                        else {}
                                    )
                                    metadata["ai_action"] = {
                                        "action_key": ai_reply.action,
                                        "sent_as_interactive": False,
                                    }
                                    sent_message.metadata_json = metadata
                                    db.commit()
                processed += 1

            for status_update in value.get("statuses", []):
                create_event(
                    db,
                    company_id=account.company_id,
                    event_type="message.status",
                    payload={
                        "message_id": status_update.get("id"),
                        "status": status_update.get("status"),
                        "recipient_id": status_update.get("recipient_id"),
                        "timestamp": status_update.get("timestamp"),
                        "raw": status_update,
                    },
                )
                db.commit()
                realtime_manager.publish(
                    account.company_id,
                    "message.status",
                    {
                        "message_id": status_update.get("id"),
                        "status": status_update.get("status"),
                        "recipient_id": status_update.get("recipient_id"),
                    },
                )
                processed += 1

    return processed, skipped

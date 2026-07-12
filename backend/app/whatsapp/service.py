from datetime import UTC, datetime
from decimal import Decimal
import logging
import re
import unicodedata
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.models import AiInteractiveTemplate
from app.ai.runtime import AutoReplyResult, generate_auto_reply
from app.audit.service import record_audit_best_effort
from app.contacts.service import get_contact, get_or_create_contact
from app.conversations.models import Conversation
from app.conversations.service import append_message, auto_assign_single_additional_user_chat, get_or_create_open_conversation
from app.core.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.ai.intent_classifier import classify_intent
from app.events.models import Event
from app.events.service import create_event
from app.inventory.models import Inventory
from app.inventory.service import available_units, ensure_inventory_for_products
from app.messages.models import Message
from app.orders.models import Order
from app.orders.schemas import OrderCreate, OrderItemCreate
from app.payments.contract import (
    clear_expired_payment_followup_reservation,
    expired_payment_followup_metadata,
    expired_payment_followup_origin_order_id,
    expired_payment_followup_sent,
    reserve_expired_payment_followup,
    record_expired_payment_followup,
)
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
        error_data = error.get("error_data") if isinstance(error, dict) else None
        meta_details = (
            str(error_data.get("details") or "").strip()
            if isinstance(error_data, dict)
            else ""
        )
        if meta_details and meta_details not in detail:
            detail = f"{detail}: {meta_details}"
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
    auto_assignment = auto_assign_single_additional_user_chat(
        db,
        company_id=account.company_id,
        conversation=conversation,
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
    if auto_assignment is not None:
        realtime_manager.publish(account.company_id, "conversation.assigned", auto_assignment)
        record_audit_best_effort(
            db,
            company_id=account.company_id,
            actor_user=None,
            action="conversation.assigned",
            entity_type="conversation",
            entity_id=conversation.id,
            summary="Conversation auto-assigned",
            metadata=auto_assignment,
        )
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


def _send_image_with_account(
    db: Session,
    *,
    account: WhatsAppAccount,
    to: str,
    image_url: str,
    caption: str,
    source: str,
    metadata: dict | None = None,
) -> WhatsAppSendTextResponse:
    recipient = _normalize_phone(to)
    meta_payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption[:1024],
        },
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
    auto_assignment = auto_assign_single_additional_user_chat(
        db,
        company_id=account.company_id,
        conversation=conversation,
    )
    message_metadata = {
        "raw": data,
        "image_url": image_url,
        "sent_at": datetime.now(UTC).isoformat(),
        "source": source,
    }
    if metadata:
        message_metadata.update(metadata)
    message = append_message(
        db,
        company_id=account.company_id,
        conversation_id=conversation.id,
        sender_type="agent",
        content=caption,
        message_type="image",
        external_message_id=meta_message_id,
        metadata=message_metadata,
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
    if auto_assignment is not None:
        realtime_manager.publish(account.company_id, "conversation.assigned", auto_assignment)
        record_audit_best_effort(
            db,
            company_id=account.company_id,
            actor_user=None,
            action="conversation.assigned",
            entity_type="conversation",
            entity_id=conversation.id,
            summary="Conversation auto-assigned",
            metadata=auto_assignment,
        )
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
    auto_assignment = auto_assign_single_additional_user_chat(
        db,
        company_id=account.company_id,
        conversation=conversation,
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
    if auto_assignment is not None:
        realtime_manager.publish(account.company_id, "conversation.assigned", auto_assignment)
        record_audit_best_effort(
            db,
            company_id=account.company_id,
            actor_user=None,
            action="conversation.assigned",
            entity_type="conversation",
            entity_id=conversation.id,
            summary="Conversation auto-assigned",
            metadata=auto_assignment,
        )
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


def _build_expired_payment_followup_text(
    db: Session,
    *,
    company_id: UUID,
    order: Order,
    conversation: Conversation,
) -> AutoReplyResult | None:
    payment_context = (
        f"Orden expirada detectada: {order.id} | "
        f"referencia: {order.payment_reference or '-'} | "
        f"estado: {order.status} | "
        f"payment_status: {order.payment_status} | "
        f"conversation_id: {conversation.id}"
    )
    ai_reply = generate_auto_reply(
        db,
        company_id=company_id,
        conversation=conversation,
        incoming_text=(
            "Seguimiento comercial de link de pago expirado. "
            "Pregunta si el cliente desea continuar con el pago o ajustar su pedido. "
            "No confirmes pagos, no extiendas vencimientos y no prometas stock."
        ),
        payment_context=payment_context,
    )
    if isinstance(ai_reply, AutoReplyResult) and ai_reply.reply_text.strip():
        return ai_reply
    return None


def send_expired_payment_followup(
    db: Session,
    *,
    order: Order,
    actor_user=None,
) -> WhatsAppSendTextResponse | None:
    if expired_payment_followup_sent(order):
        return None
    if order.conversation_id is None:
        return None

    conversation = db.scalar(
        select(Conversation).where(
            Conversation.company_id == order.company_id,
            Conversation.id == order.conversation_id,
        )
    )
    if conversation is None or conversation.status == "closed" or not conversation.ai_enabled:
        if reserve_expired_payment_followup(
            order,
            claimed_at=datetime.now(UTC),
            source="ai_payment_expired_followup_skipped",
        ):
            db.commit()
        return None

    try:
        account = get_account(db, company_id=order.company_id)
    except HTTPException:
        return None

    locked_order = db.scalar(
        select(Order)
        .where(
            Order.company_id == order.company_id,
            Order.id == order.id,
        )
        .with_for_update()
    )
    if locked_order is None:
        return None
    order = locked_order
    if not reserve_expired_payment_followup(
        order,
        claimed_at=datetime.now(UTC),
        source="ai_payment_expired_followup",
    ):
        return None
    db.commit()
    db.refresh(order)

    try:
        contact = get_contact(db, company_id=order.company_id, contact_id=conversation.contact_id)
        follow_up = _build_expired_payment_followup_text(
            db,
            company_id=order.company_id,
            order=order,
            conversation=conversation,
        )
        body = (
            follow_up.reply_text
            if isinstance(follow_up, AutoReplyResult) and follow_up.reply_text.strip()
            else "Tu link de pago vencio. Si quieres, te ayudo a continuar el pago o a revisar otro producto."
        )
        response = _send_text_with_account(
            db,
            account=account,
            to=contact.phone,
            body=body,
            source="ai_payment_expired_followup",
        )
    except Exception:
        clear_expired_payment_followup_reservation(order)
        db.commit()
        logger.exception(
            "Failed to send expired payment follow-up company_id=%s order_id=%s",
            order.company_id,
            order.id,
        )
        return None

    sent_message = db.get(Message, response.message_id)
    if sent_message is not None:
        metadata = sent_message.metadata_json if isinstance(sent_message.metadata_json, dict) else {}
        metadata["ai_action"] = {
            "action_key": "payment_expired_followup",
            "sent_as_interactive": False,
        }
        sent_message.metadata_json = metadata

    record_expired_payment_followup(
        order,
        sent_at=datetime.now(UTC),
        message_id=str(response.message_id),
        source="ai_payment_expired_followup",
    )
    db.commit()
    record_audit_best_effort(
        db,
        company_id=order.company_id,
        actor_user=actor_user,
        action="order.payment_followup_sent",
        entity_type="order",
        entity_id=order.id,
        summary="Expired payment follow-up sent",
        metadata={
            "order_id": str(order.id),
            "conversation_id": str(conversation.id),
            "message_id": str(response.message_id),
            "payment_reference": order.payment_reference,
        },
    )
    return response


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
        and conversation_status in {"open", "waiting_customer", "waiting_human"}
    )


def _build_expired_payment_context(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
) -> str:
    order = db.scalar(
        select(Order)
        .where(
            Order.company_id == company_id,
            Order.conversation_id == conversation_id,
        )
        .order_by(Order.created_at.desc())
    )
    if order is None:
        return ""
    origin_order = None
    origin_order_id = expired_payment_followup_origin_order_id(order)
    if origin_order_id:
        try:
            origin_uuid = UUID(origin_order_id)
        except ValueError:
            origin_uuid = None
        if origin_uuid is not None:
            candidate = db.get(Order, origin_uuid)
            if (
                candidate is not None
                and candidate.company_id == company_id
                and candidate.conversation_id == conversation_id
            ):
                origin_order = candidate

    follow_up_source_order = origin_order or order
    follow_up_details = expired_payment_followup_metadata(follow_up_source_order)
    follow_up = bool(follow_up_details.get("sent_at") or follow_up_details.get("claimed_at"))
    if order.status != "expired" and not follow_up and origin_order is None:
        return ""

    reference_order = origin_order or order
    payment_metadata = (
        reference_order.metadata_json if isinstance(reference_order.metadata_json, dict) else {}
    )
    payment_details = payment_metadata.get("payment", {}) if isinstance(payment_metadata, dict) else {}
    follow_up_at = follow_up_details.get("sent_at") or follow_up_details.get("claimed_at")
    return (
        "Contexto de pago vencido del hilo:\n"
        f"- Orden mas reciente: {order.id}\n"
        f"- Estado de orden mas reciente: {order.status}\n"
        f"- Orden origen del vencimiento: {origin_order.id if origin_order else '-'}\n"
        f"- Estado de orden origen: {reference_order.status}\n"
        f"- Estado de pago origen: {reference_order.payment_status}\n"
        f"- Referencia de pago activa: {order.payment_reference or reference_order.payment_reference or '-'}\n"
        f"- Expiracion persistida: {payment_details.get('expires_at') or '-'}\n"
        f"- Seguimiento automatico enviado: {'si' if follow_up_at else 'no'}\n"
        f"- Seguimiento enviado en: {follow_up_at or '-'}\n"
        "Regla: no repitas el recordatorio de expiracion si ya fue enviado; si el cliente desea continuar, "
        "usa el flujo comercial del tenant y backend para generar una nueva orden o un nuevo link. "
        "Si ya existe una orden de recuperacion, reutilizala en vez de crear otra."
    )


def _load_conversation_ai_enabled(
    db: Session, *, company_id: UUID, conversation_id: UUID
) -> bool:
    with Session(bind=db.get_bind()) as verification_db:
        value = verification_db.scalar(
            select(Conversation.ai_enabled).where(
                Conversation.company_id == company_id,
                Conversation.id == conversation_id,
            )
        )
    if value is None:
        return True
    return bool(value)


def _normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return " ".join(
        "".join(
            char
            for char in normalized
            if not unicodedata.combining(char) and (char.isalnum() or char.isspace())
        )
        .strip()
        .lower()
        .split()
    )


def _latest_order_for_conversation(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
) -> Order | None:
    return db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.company_id == company_id,
            Order.conversation_id == conversation_id,
        )
        .order_by(Order.created_at.desc())
    )


def _recovery_order_from_expired_order(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    expired_order_id: UUID,
) -> Order | None:
    orders = list(
        db.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.company_id == company_id,
                Order.conversation_id == conversation_id,
            )
            .order_by(Order.created_at.desc())
        )
    )
    for candidate in orders:
        payment_metadata = candidate.metadata_json if isinstance(candidate.metadata_json, dict) else {}
        payment_details = payment_metadata.get("payment", {}) if isinstance(payment_metadata, dict) else {}
        follow_up = payment_details.get("followup", {}) if isinstance(payment_details, dict) else {}
        if not isinstance(follow_up, dict):
            continue
        if str(follow_up.get("origin_order_id") or "").strip() != str(expired_order_id):
            continue
        return candidate
    return None


def _payment_context_orders(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
) -> tuple[Order | None, Order | None]:
    latest_order = db.scalar(
        select(Order)
        .where(
            Order.company_id == company_id,
            Order.conversation_id == conversation_id,
        )
        .order_by(Order.created_at.desc())
    )
    if latest_order is None:
        return None, None

    origin_order = None
    origin_order_id = expired_payment_followup_origin_order_id(latest_order)
    if origin_order_id:
        try:
            origin_uuid = UUID(origin_order_id)
        except ValueError:
            origin_uuid = None
        if origin_uuid is not None:
            candidate = db.get(Order, origin_uuid)
            if (
                candidate is not None
                and candidate.company_id == company_id
                and candidate.conversation_id == conversation_id
            ):
                origin_order = candidate

    return latest_order, origin_order


def _customer_requests_payment_continuation(message_content: str | None) -> bool:
    normalized = _normalize_search_text(message_content or "")
    if not normalized:
        return False
    human_handoff_keywords = (
        "asesor",
        "humano",
        "persona",
        "agente",
        "soporte",
        "problema",
        "garantia",
        "queja",
        "reclamo",
    )
    if any(keyword in normalized for keyword in human_handoff_keywords):
        return False
    if classify_intent(message_content or "").intent == "buy_product":
        return True
    affirmative_keywords = (
        "si",
        "dale",
        "ok",
        "okay",
        "listo",
        "va",
        "adelante",
        "confirmo",
        "claro",
    )
    if normalized in affirmative_keywords or any(
        normalized.startswith(f"{keyword} ") for keyword in affirmative_keywords
    ):
        return True
    continuation_keywords = (
        "continuar",
        "seguir",
        "pagar",
        "pago",
        "nuevo link",
        "nuevo pago",
        "otro link",
        "otro pedido",
        "repetir",
        "otra vez",
        "checkout",
    )
    return any(keyword in normalized for keyword in continuation_keywords)


def _clone_expired_order_for_new_payment(
    db: Session,
    *,
    expired_order: Order,
    actor_user=None,
) -> Order | None:
    from app.orders.service import create_order, generate_payment_link

    if expired_order.conversation_id is None:
        return None
    if expired_order.items is None:
        return None

    existing_recovery_order = _recovery_order_from_expired_order(
        db,
        company_id=expired_order.company_id,
        conversation_id=expired_order.conversation_id,
        expired_order_id=expired_order.id,
    )
    if existing_recovery_order is not None:
        if existing_recovery_order.payment_link:
            return existing_recovery_order
        try:
            return generate_payment_link(
                db,
                company_id=expired_order.company_id,
                order_id=existing_recovery_order.id,
                actor_user=actor_user,
            )
        except Exception:
            logger.exception(
                "Failed to regenerate payment link for recovery order company_id=%s order_id=%s",
                expired_order.company_id,
                existing_recovery_order.id,
            )
            return None

    payload = OrderCreate(
        contact_id=expired_order.contact_id,
        conversation_id=expired_order.conversation_id,
        items=[
            OrderItemCreate(product_id=item.product_id, quantity=item.quantity)
            for item in expired_order.items
        ],
        metadata={
            "idempotency_key": f"expired-followup:{expired_order.id}",
            "payment": {
                "followup": {
                    "origin_order_id": str(expired_order.id),
                    "source": "expired_payment_followup",
                }
            },
        },
    )
    new_order = create_order(
        db,
        company_id=expired_order.company_id,
        payload=payload,
        actor_user=actor_user,
    )
    try:
        return generate_payment_link(
            db,
            company_id=expired_order.company_id,
            order_id=new_order.id,
            actor_user=actor_user,
        )
    except Exception:
        logger.exception(
            "Failed to generate payment link for recovery order company_id=%s order_id=%s",
            expired_order.company_id,
            new_order.id,
        )
        return None


def _build_expired_payment_recovery_text(
    ai_reply: AutoReplyResult | None,
    *,
    payment_link: str,
) -> str:
    intro = "Tu link de pago vencio. Te comparto uno nuevo para continuar."
    if isinstance(ai_reply, AutoReplyResult) and ai_reply.reply_text.strip():
        intro = ai_reply.reply_text.strip()
    if payment_link.strip():
        return f"{intro}\n{payment_link.strip()}"
    return intro


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
    _require_catalog_connected_to_waba(account=account, catalog_id=payload.catalog_id)
    requested_retailer_ids = [item.product_retailer_id for item in payload.items]
    available_products = _list_available_products_for_retailer_ids(
        db,
        company_id=company_id,
        retailer_ids=requested_retailer_ids,
        catalog_id=payload.catalog_id,
    )
    if len(available_products) != len(requested_retailer_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Some selected products have no confirmed stock",
        )
    if len(payload.items) == 1:
        interactive_payload = {
            "type": "product",
            "body": {"text": payload.body},
            "action": {
                "catalog_id": payload.catalog_id,
                "product_retailer_id": available_products[0][0].whatsapp_product_retailer_id,
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
                            {"product_retailer_id": product.whatsapp_product_retailer_id}
                            for product, _inventory in available_products
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
    active_products = list(
        db.scalars(
            select(Product).where(
                Product.company_id == company_id,
                Product.id.in_(payload.product_ids),
                Product.status == "active",
            )
        )
    )
    if not active_products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active products found for selected ids",
        )
    products_by_id = {product.id: product for product in active_products}
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
    _require_catalog_connected_to_waba(account=account, catalog_id=catalog_id)
    available_products = _list_available_products_for_product_ids(
        db,
        company_id=company_id,
        product_ids=[product.id for product in products],
        catalog_id=catalog_id,
    )
    if len(available_products) != len(products):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Some selected products have no confirmed stock",
        )
    items = [
        {"product_retailer_id": product.whatsapp_product_retailer_id}
        for product, _inventory in available_products
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


def _available_product_rows_stmt(
    *,
    company_id: UUID,
    catalog_id: str | None = None,
    product_ids: list[UUID] | None = None,
    retailer_ids: list[str] | None = None,
):
    stmt = (
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
            Inventory.available_units > 0,
        )
    )
    if catalog_id is not None:
        stmt = stmt.where(Product.whatsapp_catalog_id == catalog_id)
    if product_ids is not None:
        stmt = stmt.where(Product.id.in_(product_ids))
    if retailer_ids is not None:
        stmt = stmt.where(Product.whatsapp_product_retailer_id.in_(retailer_ids))
    return stmt


def _list_available_products_for_retailer_ids(
    db: Session,
    *,
    company_id: UUID,
    retailer_ids: list[str],
    catalog_id: str,
) -> list[tuple[Product, Inventory]]:
    normalized_ids = [str(retailer_id).strip() for retailer_id in retailer_ids if str(retailer_id).strip()]
    if not normalized_ids:
        return []
    rows = list(
        db.execute(
            _available_product_rows_stmt(
                company_id=company_id,
                catalog_id=catalog_id,
                retailer_ids=normalized_ids,
            )
        )
    )
    rows_by_retailer_id = {
        product.whatsapp_product_retailer_id: (product, inventory)
        for product, inventory in rows
        if product.whatsapp_product_retailer_id
    }
    return [
        rows_by_retailer_id[retailer_id]
        for retailer_id in normalized_ids
        if retailer_id in rows_by_retailer_id
    ]


def _list_available_products_for_product_ids(
    db: Session,
    *,
    company_id: UUID,
    product_ids: list[UUID],
    catalog_id: str,
) -> list[tuple[Product, Inventory]]:
    if not product_ids:
        return []
    rows = list(
        db.execute(
            _available_product_rows_stmt(
                company_id=company_id,
                catalog_id=catalog_id,
                product_ids=product_ids,
            )
        )
    )
    rows_by_product_id = {product.id: (product, inventory) for product, inventory in rows}
    return [
        rows_by_product_id[product_id]
        for product_id in product_ids
        if product_id in rows_by_product_id
    ]


def _product_card_caption(product: Product, inventory: Inventory) -> str:
    available = available_units(inventory)
    description = re.sub(r"\s+", " ", product.description or "").strip()
    parts = [
        product.name,
        _format_product_price(product),
        f"Disponible: {available} unidades",
    ]
    if description:
        parts.append(description[:700])
    return "\n".join(parts)


def _send_product_image_cards_from_db(
    db: Session,
    *,
    account: WhatsAppAccount,
    to: str,
    product_ids: list[UUID],
    intro: str,
    limit: int = 5,
) -> bool:
    rows = list(
        db.execute(
            select(Product, Inventory)
            .join(
                Inventory,
                (Inventory.company_id == Product.company_id)
                & (Inventory.product_id == Product.id),
            )
            .where(
                Product.company_id == account.company_id,
                Product.id.in_(product_ids),
                Product.status == "active",
                Inventory.available_units > 0,
            )
        )
    )
    rows_by_id = {product.id: (product, inventory) for product, inventory in rows}
    sent_any = False
    for product_id in product_ids[:limit]:
        row = rows_by_id.get(product_id)
        if row is None:
            continue
        product, inventory = row
        product_metadata = (
            product.metadata_json if isinstance(product.metadata_json, dict) else {}
        )
        image_url = str(product_metadata.get("image_url") or "").strip()
        if not image_url:
            continue
        _send_image_with_account(
            db,
            account=account,
            to=to,
            image_url=image_url,
            caption=_product_card_caption(product, inventory),
            source="agent_product_image_card",
            metadata={
                "product_id": str(product.id),
                "catalog_id": product.whatsapp_catalog_id,
                "product_retailer_id": product.whatsapp_product_retailer_id,
                "fallback_from": "agent_product_cards_db",
            },
        )
        sent_any = True
    if sent_any and intro.strip():
        _send_text_with_account(
            db,
            account=account,
            to=to,
            body=(
                "Te comparti las opciones disponibles en tarjetas. "
                "Dime cual te gusta y seguimos con tu compra."
            ),
            source="agent_product_image_card_followup",
        )
    return sent_any


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
        and available_units(inventory) > 0
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
                Inventory.available_units > 0,
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


def _message_requests_catalog(message_content: str, interactive_reply: dict | None) -> bool:
    if _interactive_reply_requests_catalog(interactive_reply):
        return True
    normalized = (
        "".join(
            char
            for char in unicodedata.normalize("NFKD", message_content)
            if not unicodedata.combining(char)
        )
        .strip()
        .lower()
    )
    return any(keyword in normalized for keyword in ("producto", "catalogo", "bronceador"))


def _format_product_price(product: Product) -> str:
    amount = f"{product.price:,.0f}".replace(",", ".")
    return f"${amount} {product.currency}"


def _build_available_products_fallback(
    db: Session,
    *,
    company_id: UUID,
    product_ids: list[UUID],
    intro: str,
) -> str:
    if not product_ids:
        return intro
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
                Product.id.in_(product_ids),
                Product.status == "active",
                Inventory.available_units > 0,
            )
        )
    )
    rows_by_id = {product.id: (product, inventory) for product, inventory in rows}
    lines: list[str] = []
    for product_id in product_ids[:5]:
        row = rows_by_id.get(product_id)
        if row is None:
            continue
        product, inventory = row
        description = re.sub(r"\s+", " ", product.description or "").strip()
        details = f" {description[:140]}" if description else ""
        available = available_units(inventory)
        lines.append(
            f"- {product.name}: {_format_product_price(product)}. "
            f"Disponible ({available} unidades).{details}"
        )
    if not lines:
        return intro
    return (
        f"{intro.strip()}\n\n"
        "Estos productos tienen disponibilidad confirmada:\n"
        f"{chr(10).join(lines)}\n\n"
        "Cuéntame cuál te interesa y te ayudo a elegir."
    )[:4096]


def _catalog_link_warning(*, account: WhatsAppAccount, catalog_id: str) -> str | None:
    try:
        data = _meta_request(
            "GET",
            f"/{account.business_account_id}/product_catalogs",
            access_token=decrypt_secret(account.access_token_encrypted),
        )
    except HTTPException as exc:
        logger.warning(
            "Unable to validate WhatsApp catalog link waba_id=%s catalog_id=%s detail=%s",
            account.business_account_id,
            catalog_id,
            exc.detail,
        )
        return None

    rows = data.get("data", []) if isinstance(data, dict) else []
    linked_catalog_ids = {
        str(row.get("id") or "").strip()
        for row in rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    if catalog_id in linked_catalog_ids:
        return None
    return (
        f"El catalogo Meta {catalog_id} se puede leer, pero no esta vinculado a la cuenta "
        f"de WhatsApp Business {account.business_account_id}. Vinculalo en WhatsApp Manager "
        "antes de enviar cards de productos."
    )


def _require_catalog_connected_to_waba(*, account: WhatsAppAccount, catalog_id: str) -> None:
    warning = _catalog_link_warning(account=account, catalog_id=catalog_id)
    if warning:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=warning,
        )


def _fetch_catalog_product_rows(*, account: WhatsAppAccount, catalog_id: str) -> list[dict]:
    fields = (
        "retailer_id,name,description,price,currency,availability,inventory,"
        "image_url,url,visibility"
    )
    after: str | None = None
    rows: list[dict] = []
    for _page in range(20):
        params = {"fields": fields, "limit": "100"}
        if after:
            params["after"] = after
        data = _meta_request(
            "GET",
            f"/{catalog_id}/products",
            access_token=decrypt_secret(account.access_token_encrypted),
            params=params,
        )
        batch = data.get("data", []) if isinstance(data, dict) else []
        if isinstance(batch, list):
            rows.extend(row for row in batch if isinstance(row, dict))
        paging = data.get("paging", {}) if isinstance(data, dict) else {}
        cursors = paging.get("cursors", {}) if isinstance(paging, dict) else {}
        next_after = str(cursors.get("after") or "").strip()
        if not paging.get("next") or not next_after or next_after == after:
            break
        after = next_after
    return rows


def _meta_inventory_quantity(row: dict, *, availability: str) -> int | None:
    if availability in {"out of stock", "discontinued"}:
        return 0
    raw_inventory = row.get("inventory")
    if raw_inventory is None:
        return None
    try:
        return max(0, int(raw_inventory))
    except (TypeError, ValueError):
        return None


def _sync_catalog_products_with_account(
    db: Session,
    *,
    company_id: UUID,
    account: WhatsAppAccount,
    catalog_id: str,
) -> WhatsAppCatalogSyncResponse:
    rows = _fetch_catalog_product_rows(account=account, catalog_id=catalog_id)
    created = 0
    updated = 0
    skipped_invalid_price = 0
    inventory_quantities: dict[str, int | None] = {}
    for row in rows:
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
        availability = str(row.get("availability") or "").strip().lower()
        status = "inactive" if availability in {"out of stock", "discontinued"} else "active"
        price = _to_decimal_price(row.get("price"))
        if price <= 0:
            skipped_invalid_price += 1
            continue
        metadata = {
            "source": "meta_catalog_sync",
            "availability": availability,
            "image_url": str(row.get("image_url") or "").strip() or None,
            "product_url": str(row.get("url") or "").strip() or None,
            "visibility": str(row.get("visibility") or "").strip() or None,
            "synced_at": datetime.now(UTC).isoformat(),
        }
        inventory_quantities[retailer_id] = _meta_inventory_quantity(
            row, availability=availability
        )

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
                    whatsapp_catalog_id=catalog_id,
                    whatsapp_product_retailer_id=retailer_id,
                    metadata_json=metadata,
                )
            )
            created += 1
        else:
            existing.name = name
            existing.description = description
            existing.price = price
            existing.currency = currency
            existing.status = status
            existing.whatsapp_catalog_id = catalog_id
            current_metadata = (
                dict(existing.metadata_json)
                if isinstance(existing.metadata_json, dict)
                else {}
            )
            current_metadata.update(metadata)
            existing.metadata_json = current_metadata
            updated += 1

    db.flush()
    ensure_inventory_for_products(db, company_id=company_id)
    db.flush()
    inventory_rows = list(
        db.execute(
            select(Product, Inventory)
            .join(
                Inventory,
                (Inventory.company_id == Product.company_id)
                & (Inventory.product_id == Product.id),
            )
            .where(
                Product.company_id == company_id,
                Product.whatsapp_catalog_id == catalog_id,
            )
        )
    )
    for product, inventory in inventory_rows:
        retailer_id = product.whatsapp_product_retailer_id or ""
        if retailer_id not in inventory_quantities:
            product.status = "inactive"
            inventory.quantity_available = 0
            continue
        quantity = inventory_quantities.get(retailer_id)
        if quantity is not None:
            inventory.quantity_available = quantity
    db.commit()
    warning_messages = []
    if skipped_invalid_price:
        warning_messages.append(
            f"Se omitieron {skipped_invalid_price} productos de Meta con precio invalido."
        )
    link_warning = _catalog_link_warning(account=account, catalog_id=catalog_id)
    if link_warning:
        warning_messages.append(link_warning)
    return WhatsAppCatalogSyncResponse(
        fetched=len(rows),
        created=created,
        updated=updated,
        warning=" ".join(warning_messages) if warning_messages else None,
    )


def _sync_linked_catalogs_for_product_query(
    db: Session,
    *,
    account: WhatsAppAccount,
) -> None:
    try:
        data = _meta_request(
            "GET",
            f"/{account.business_account_id}/product_catalogs",
            access_token=decrypt_secret(account.access_token_encrypted),
        )
        rows = data.get("data", []) if isinstance(data, dict) else []
        for row in rows if isinstance(rows, list) else []:
            catalog_id = str(row.get("id") or "").strip() if isinstance(row, dict) else ""
            if catalog_id:
                _sync_catalog_products_with_account(
                    db,
                    company_id=account.company_id,
                    account=account,
                    catalog_id=catalog_id,
                )
    except HTTPException as exc:
        logger.warning(
            "Automatic catalog sync skipped company_id=%s detail=%s",
            account.company_id,
            exc.detail,
        )


def sync_catalog_products(
    db: Session,
    *,
    company_id: UUID,
    payload: WhatsAppCatalogSyncRequest,
) -> WhatsAppCatalogSyncResponse:
    account = get_account(db, company_id=company_id, account_id=payload.account_id)
    try:
        return _sync_catalog_products_with_account(
            db,
            company_id=company_id,
            account=account,
            catalog_id=payload.catalog_id,
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
                message_processed = False
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
                auto_assignment = auto_assign_single_additional_user_chat(
                    db,
                    company_id=account.company_id,
                    conversation=conversation,
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
                if auto_assignment is not None:
                    realtime_manager.publish(
                        account.company_id,
                        "conversation.assigned",
                        auto_assignment,
                    )
                    record_audit_best_effort(
                        db,
                        company_id=account.company_id,
                        actor_user=None,
                        action="conversation.assigned",
                        entity_type="conversation",
                        entity_id=conversation.id,
                        summary="Conversation auto-assigned",
                        metadata=auto_assignment,
                    )
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
                db.refresh(conversation, attribute_names=["ai_enabled", "status"])
                if conversation.ai_enabled and _should_generate_auto_reply(
                    message_type=message_type,
                    content=message_content,
                    conversation_status=conversation.status,
                ):
                    catalog_requested = _message_requests_catalog(
                        message_content or "",
                        interactive_reply,
                    )
                    catalog_refreshed = catalog_requested
                    if catalog_requested:
                        _sync_linked_catalogs_for_product_query(db, account=account)
                    ai_reply = generate_auto_reply(
                        db,
                        company_id=account.company_id,
                        conversation=conversation,
                        incoming_text=message_content,
                        incoming_interactive_reply=interactive_reply,
                        payment_context=_build_expired_payment_context(
                            db,
                            company_id=account.company_id,
                            conversation_id=conversation.id,
                        )
                        or None,
                    )
                    if ai_reply is None and catalog_requested:
                        ai_reply = AutoReplyResult(
                            reply_text=(
                                "Claro, te comparto productos disponibles para que elijas "
                                "el que mejor se adapte a lo que buscas."
                            )
                        )
                    if ai_reply:
                        if not _load_conversation_ai_enabled(
                            db,
                            company_id=account.company_id,
                            conversation_id=conversation.id,
                        ):
                            logger.info(
                                "AI auto-reply aborted after generation: conversation paused company_id=%s conversation_id=%s",
                                account.company_id,
                                conversation.id,
                            )
                            processed += 1
                            message_processed = True
                            continue
                        product_cards_sent = False
                        action_sent = False
                        product_ids: list[UUID] = []
                        recovery_attempted = False
                        recovery_link_ready = False
                        suppress_generic_reply = False
                        reply_text = (
                            ai_reply.reply_text
                            if isinstance(ai_reply, AutoReplyResult)
                            else str(ai_reply)
                        )
                        if isinstance(ai_reply, AutoReplyResult):
                            ai_reply.action = _resolve_configured_action(
                                db,
                                account=account,
                                conversation=conversation,
                                contact=contact,
                                ai_reply=ai_reply,
                            )
                            expired_order = _latest_order_for_conversation(
                                db,
                                company_id=account.company_id,
                                conversation_id=conversation.id,
                            )
                            recovery_order = None
                            recovery_origin_order = None
                            if expired_order is not None and expired_order.status in {"pending", "waiting_payment"}:
                                recovery_origin_order_id = expired_payment_followup_origin_order_id(expired_order)
                                if recovery_origin_order_id:
                                    try:
                                        recovery_origin_uuid = UUID(recovery_origin_order_id)
                                    except ValueError:
                                        recovery_origin_uuid = None
                                    if recovery_origin_uuid is not None:
                                        candidate_origin = db.get(Order, recovery_origin_uuid)
                                        if candidate_origin is not None and candidate_origin.status == "expired":
                                            recovery_origin_order = candidate_origin
                            if (
                                expired_order is not None
                                and expired_order.status == "expired"
                                and _customer_requests_payment_continuation(message_content)
                            ):
                                recovery_attempted = True
                                recovery_order = _clone_expired_order_for_new_payment(
                                    db,
                                    expired_order=expired_order,
                                    actor_user=None,
                                )
                            elif (
                                recovery_origin_order is not None
                                and _customer_requests_payment_continuation(message_content)
                            ):
                                recovery_attempted = True
                                recovery_order = _clone_expired_order_for_new_payment(
                                    db,
                                    expired_order=recovery_origin_order,
                                    actor_user=None,
                                )
                            recovery_link_ready = recovery_order is not None and bool(recovery_order.payment_link)
                            if recovery_link_ready:
                                recovery_body = _build_expired_payment_recovery_text(
                                    ai_reply,
                                    payment_link=recovery_order.payment_link,
                                )
                                response = _send_text_with_account(
                                    db,
                                    account=account,
                                    to=customer_phone,
                                    body=recovery_body,
                                    source="ai_payment_followup_recovery",
                                )
                                sent_message = db.get(Message, response.message_id)
                                if sent_message is not None:
                                    metadata = (
                                        sent_message.metadata_json
                                        if isinstance(sent_message.metadata_json, dict)
                                        else {}
                                    )
                                    metadata["ai_action"] = {
                                        "action_key": "payment_recovery_link",
                                        "sent_as_interactive": False,
                                    }
                                    metadata["payment_followup"] = {
                                        "origin_order_id": str(
                                            recovery_origin_order.id if recovery_origin_order is not None else expired_order.id
                                        ),
                                        "recovery_order_id": str(recovery_order.id),
                                    }
                                    sent_message.metadata_json = metadata
                                    db.commit()
                                processed += 1
                                message_processed = True
                                if not (catalog_requested or ai_reply.product_retailer_ids):
                                    continue
                            elif recovery_attempted:
                                suppress_generic_reply = True
                                logger.info(
                                    "AI payment recovery requested but link generation failed company_id=%s conversation_id=%s",
                                    account.company_id,
                                    conversation.id,
                                )
                            if recovery_attempted and not recovery_link_ready:
                                reply_text = (
                                    "Puedo ayudarte a revisar otra opción para continuar tu compra."
                                )
                            if ai_reply.product_retailer_ids and not catalog_refreshed:
                                _sync_linked_catalogs_for_product_query(db, account=account)
                                catalog_refreshed = True
                            product_ids = _resolve_available_product_ids(
                                db,
                                company_id=account.company_id,
                                retailer_ids=ai_reply.product_retailer_ids,
                            )
                        if catalog_requested and not product_ids:
                            product_ids = _list_available_product_ids(
                                db,
                                company_id=account.company_id,
                            )
                        if product_ids:
                            try:
                                logger.info(
                                    "AI product cards attempt company_id=%s count=%s catalog_requested=%s",
                                    account.company_id,
                                    len(product_ids),
                                    catalog_requested,
                                )
                                send_product_cards_from_db(
                                    db,
                                    company_id=account.company_id,
                                    payload=WhatsAppSendProductCardsFromDbRequest(
                                        to=customer_phone,
                                        body=reply_text[:1024],
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
                                try:
                                    product_cards_sent = _send_product_image_cards_from_db(
                                        db,
                                        account=account,
                                        to=customer_phone,
                                        product_ids=product_ids,
                                        intro=reply_text,
                                    )
                                except HTTPException as image_exc:
                                    logger.warning(
                                        "AI product image cards skipped company_id=%s detail=%s",
                                        account.company_id,
                                        image_exc.detail,
                                    )
                                if not product_cards_sent:
                                    fallback = _build_available_products_fallback(
                                        db,
                                        company_id=account.company_id,
                                        product_ids=product_ids,
                                        intro=reply_text,
                                    )
                                    if isinstance(ai_reply, AutoReplyResult):
                                        ai_reply.reply_text = fallback
                                    else:
                                        ai_reply = fallback
                        elif catalog_requested:
                            logger.info(
                                "AI product cards no available products company_id=%s",
                                account.company_id,
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
                                    fallback_text=reply_text,
                                )
                                is not None
                            )
                        if not product_cards_sent and not action_sent:
                            if suppress_generic_reply:
                                processed += 1
                                message_processed = True
                                continue
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
                if not message_processed:
                    processed += 1

            for status_update in value.get("statuses", []):
                status_message = db.scalar(
                    select(Message).where(
                        Message.company_id == account.company_id,
                        Message.external_message_id == status_update.get("id"),
                    )
                )
                conversation_id = (
                    str(status_message.conversation_id) if status_message is not None else None
                )
                if conversation_id is None:
                    fallback_event = db.scalar(
                        select(Event).where(
                            Event.company_id == account.company_id,
                            Event.event_type == "message.sent",
                            Event.payload["meta_message_id"].as_string()
                            == status_update.get("id"),
                        ).order_by(Event.created_at.desc(), Event.id.desc())
                    )
                    if fallback_event is not None:
                        payload = fallback_event.payload if isinstance(fallback_event.payload, dict) else {}
                        if isinstance(payload.get("conversation_id"), str):
                            conversation_id = payload["conversation_id"]
                event_payload = {
                    "message_id": status_update.get("id"),
                    "status": status_update.get("status"),
                    "recipient_id": status_update.get("recipient_id"),
                    "timestamp": status_update.get("timestamp"),
                    "raw": status_update,
                }
                if conversation_id is not None:
                    event_payload["conversation_id"] = conversation_id
                create_event(
                    db,
                    company_id=account.company_id,
                    event_type="message.status",
                    payload=event_payload,
                )
                db.commit()
                if conversation_id is not None:
                    realtime_manager.publish(
                        account.company_id,
                        "message.status",
                        {
                            "conversation_id": conversation_id,
                            "message_id": status_update.get("id"),
                            "status": status_update.get("status"),
                            "recipient_id": status_update.get("recipient_id"),
                        },
                    )
                processed += 1

    return processed, skipped

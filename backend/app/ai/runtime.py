from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import unicodedata
from uuid import UUID

import httpx
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.ai.models import AiAgent, AiFaqEntry, AiInteractiveTemplate
from app.ai.intent_classifier import classify_intent
from app.ai.operational import (
    build_operational_config,
    evaluate_business_hours,
    get_effective_operational_section,
    summarize_operational_config,
)
from app.events.models import Event
from app.companies.models import Company
from app.conversations.models import Conversation
from app.funnels.models import SalesFunnel
from app.inventory.models import Inventory
from app.inventory.service import available_units
from app.messages.models import Message
from app.orders.models import Order
from app.payments.contract import (
    expired_payment_followup_metadata,
    expired_payment_followup_origin_order_id,
    order_payment_metadata,
)
from app.products.models import Product
from app.products.service import is_meta_synced_product
from app.core.config import get_settings

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
logger = logging.getLogger(__name__)
GREETING_HINTS = {
    "hola",
    "buen dia",
    "buenas",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "hello",
    "hi",
}


def _stringify_price(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def _as_bool(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "si", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return default


def _as_text(value: object, *, default: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    return default


def _as_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_json_context(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "{}"
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _messages_after_memory_reset(
    messages: list[Message],
    *,
    memory_reset_at: datetime | None = None,
    memory_reset_after_message_id: UUID | None = None,
) -> list[Message]:
    if memory_reset_after_message_id is not None:
        filtered_messages: list[Message] = []
        seen_marker = False
        for message in messages:
            if seen_marker:
                filtered_messages.append(message)
                continue
            if message.id == memory_reset_after_message_id:
                seen_marker = True
        if seen_marker:
            return filtered_messages
    cutoff = _normalize_utc(memory_reset_at)
    if cutoff is None:
        return messages
    cutoff = cutoff - timedelta(seconds=1)
    return [
        message
        for message in messages
        if (created_at := _normalize_utc(message.created_at)) is not None and created_at >= cutoff
    ]


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _load_latest_conversation_ai_enabled(db: Session, *, company_id: UUID, conversation_id: UUID) -> bool:
    with Session(bind=db.get_bind()) as verification_db:
        value = verification_db.scalar(
            select(Conversation.ai_enabled).where(
                Conversation.company_id == company_id,
                Conversation.id == conversation_id,
            )
        )
    if value is None:
        return False
    return bool(value)


def _appointment_preference_pending(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    memory_reset_at: datetime | None = None,
) -> bool:
    stmt = select(Event).where(
        Event.company_id == company_id,
        Event.event_type.in_(
            {
                "conversation.appointment_intent_prepared",
                "conversation.appointment_preference_selected",
            }
        ),
        Event.payload["conversation_id"].as_string() == str(conversation_id),
    )
    relevant_events = list(db.scalars(stmt.order_by(Event.created_at.desc(), Event.id.desc())))
    cutoff = _normalize_utc(memory_reset_at)
    if cutoff is not None:
        cutoff = cutoff - timedelta(seconds=1)
        relevant_events = [
            event
            for event in relevant_events
            if (created_at := _normalize_utc(event.created_at)) is not None and created_at >= cutoff
        ]
    latest_relevant_event = relevant_events[0] if relevant_events else None
    return latest_relevant_event is not None and latest_relevant_event.event_type == "conversation.appointment_intent_prepared"


def _normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return " ".join(
        "".join(char for char in normalized if not unicodedata.combining(char))
        .strip()
        .lower()
        .split()
    )


def _is_greeting(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return normalized in GREETING_HINTS


def _customer_message_count(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    memory_reset_at: datetime | None = None,
    memory_reset_after_message_id: UUID | None = None,
) -> int:
    stmt = select(Message).where(
        Message.company_id == company_id,
        Message.conversation_id == conversation_id,
        Message.sender_type == "customer",
        Message.content.is_not(None),
    )
    messages = list(db.scalars(stmt))
    messages = _messages_after_memory_reset(
        messages,
        memory_reset_at=memory_reset_at,
        memory_reset_after_message_id=memory_reset_after_message_id,
    )
    return len(messages)


def _build_catalog_context(db: Session, *, company_id: UUID, limit: int = 20) -> str:
    product_rows = list(
        db.execute(
            select(Product, Inventory)
            .outerjoin(
                Inventory,
                and_(
                    Inventory.company_id == Product.company_id,
                    Inventory.product_id == Product.id,
                ),
            )
            .where(
                Product.company_id == company_id,
                Product.status == "active",
                Product.whatsapp_catalog_id.is_not(None),
                Product.whatsapp_product_retailer_id.is_not(None),
            )
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
    )
    if not product_rows:
        return "Catalogo interno para consulta: sin productos activos."

    rows: list[str] = []
    for product, inventory in product_rows:
        if not is_meta_synced_product(product):
            continue
        price = _stringify_price(product.price)
        sku = product.sku or "-"
        description = " ".join((product.description or "sin descripcion").split())[:500]
        if inventory is None:
            stock = "SIN INVENTARIO CONFIGURADO: no ofrecer"
        else:
            real_available = max(0, available_units(inventory))
            stock = (
                f"Stock real disponible: {real_available} "
                f"(stock: {inventory.quantity_available}, reservado: {inventory.quantity_reserved})"
            )
            if real_available <= 0:
                stock += " | NO DISPONIBLE: no ofrecer"
        rows.append(
            f"- {product.name} | SKU: {sku} | Meta retailer_id: "
            f"{product.whatsapp_product_retailer_id or 'SIN MAPEO META'} | "
            f"Descripcion: {description} | Precio: {price} {product.currency} | {stock}"
        )
    return (
        "Catalogo e inventario interno para consulta obligatoria de la IA, "
        "no lo envies completo al cliente:\n" + "\n".join(rows)
    )


def _build_recent_conversation_context(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    limit: int = 14,
    memory_reset_at: datetime | None = None,
    memory_reset_after_message_id: UUID | None = None,
) -> list[dict[str, str]]:
    stmt = select(Message).where(
        Message.company_id == company_id,
        Message.conversation_id == conversation_id,
        Message.content.is_not(None),
    )
    messages = list(db.scalars(stmt.order_by(Message.created_at.desc())))
    messages = _messages_after_memory_reset(
        messages,
        memory_reset_at=memory_reset_at,
        memory_reset_after_message_id=memory_reset_after_message_id,
    )
    messages = messages[:limit]
    chat_messages: list[dict[str, str]] = []
    for message in reversed(messages):
        content = (message.content or "").strip()
        if not content:
            continue
        role = "assistant" if message.sender_type == "agent" else "user"
        chat_messages.append({"role": role, "content": content})
    return chat_messages


def _payment_context_orders(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    memory_reset_at: datetime | None = None,
    memory_reset_after_message_id: UUID | None = None,
) -> tuple[Order | None, Order | None]:
    stmt = select(Order).where(
        Order.company_id == company_id,
        Order.conversation_id == conversation_id,
    )
    orders = list(db.scalars(stmt.order_by(Order.created_at.desc())))
    if memory_reset_after_message_id is not None:
        # Orders are not message-ordered, so fall back to the timestamp cutoff for them.
        memory_reset_after_message_id = None
    cutoff = _normalize_utc(memory_reset_at)
    if cutoff is not None:
        cutoff = cutoff - timedelta(seconds=1)
        orders = [
            order
            for order in orders
            if (created_at := _normalize_utc(order.created_at)) is not None and created_at >= cutoff
        ]
    latest_order = orders[0] if orders else None
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


def _build_payment_context(
    db: Session,
    *,
    company_id: UUID,
    conversation_id: UUID,
    memory_reset_at: datetime | None = None,
    memory_reset_after_message_id: UUID | None = None,
) -> str:
    order, origin_order = _payment_context_orders(
        db,
        company_id=company_id,
        conversation_id=conversation_id,
        memory_reset_at=memory_reset_at,
        memory_reset_after_message_id=memory_reset_after_message_id,
    )
    if order is None:
        return ""

    follow_up_source_order = origin_order or order
    follow_up_metadata = expired_payment_followup_metadata(follow_up_source_order)
    if order.status != "expired" and not follow_up_metadata.get("sent_at") and origin_order is None:
        return ""
    reference_order = origin_order or order
    payment_metadata = order_payment_metadata(reference_order)
    payment_link_expires_at = str(payment_metadata.get("expires_at") or "").strip() or "-"
    follow_up_sent_at = str(follow_up_metadata.get("sent_at") or "").strip() or "-"
    follow_up_source = str(follow_up_metadata.get("source") or "").strip() or "-"
    follow_up_sent = "si" if follow_up_metadata.get("sent_at") else "no"
    return (
        "Contexto de pago del hilo:\n"
        f"- Orden mas reciente: {order.id}\n"
        f"- Estado de orden mas reciente: {order.status}\n"
        f"- Orden origen del vencimiento: {origin_order.id if origin_order else '-'}\n"
        f"- Estado de orden origen: {reference_order.status}\n"
        f"- Estado de pago origen: {reference_order.payment_status}\n"
        f"- Referencia de pago activa: {order.payment_reference or reference_order.payment_reference or '-'}\n"
        f"- Link de pago: {'presente' if order.payment_link else 'ausente'}\n"
        f"- Expiracion persistida: {payment_link_expires_at}\n"
        f"- Seguimiento automatico enviado: {follow_up_sent}\n"
        f"- Seguimiento enviado en: {follow_up_sent_at}\n"
        f"- Origen del seguimiento: {follow_up_source}\n"
        "Regla: si el seguimiento automatico ya fue enviado, no repitas el aviso de expiracion; "
        "continua la conversacion comercial y usa backend para una nueva orden o un nuevo link "
        "solo si el cliente lo pide o el flujo lo requiere. Si ya existe una orden de recuperacion, "
        "reutilizala en vez de crear otra."
    )


def _build_faq_context(db: Session, *, company_id: UUID, limit: int = 10) -> str:
    entries = list(
        db.scalars(
            select(AiFaqEntry)
            .where(AiFaqEntry.company_id == company_id, AiFaqEntry.active.is_(True))
            .order_by(AiFaqEntry.updated_at.desc())
            .limit(limit)
        )
    )
    if not entries:
        return "FAQ base: sin preguntas frecuentes definidas."
    lines = [f"- Q: {entry.question}\n  A: {entry.answer}" for entry in entries]
    return "FAQ base:\n" + "\n".join(lines)


def _get_active_agent(db: Session, *, company_id: UUID) -> AiAgent | None:
    return db.scalar(
        select(AiAgent)
        .where(AiAgent.company_id == company_id, AiAgent.active.is_(True))
        .order_by(AiAgent.updated_at.desc())
    )


def _list_active_action_templates(
    db: Session, *, company_id: UUID
) -> list[AiInteractiveTemplate]:
    return list(
        db.scalars(
            select(AiInteractiveTemplate).where(
                AiInteractiveTemplate.company_id == company_id,
                AiInteractiveTemplate.active.is_(True),
            )
        )
    )


def _build_interactive_actions_context(
    templates: list[AiInteractiveTemplate],
) -> str:
    if not templates:
        return "Biblioteca de interactivos: sin acciones disponibles."

    rows: list[str] = []
    for template in templates:
        options = template.options if isinstance(template.options, list) else []
        option_titles = [
            str(option.get("title") or "").strip()
            for option in options
            if str(option.get("title") or "").strip()
        ]
        rows.append(
            f"- action_key: {template.action_key} | nombre: {template.name} | "
            f"tipo: {template.template_type} | texto: {template.body_text} | "
            f"opciones: {', '.join(option_titles) if option_titles else 'sin opciones'} | "
            f"regla_de_uso: {template.usage_instruction or 'la IA decide segun el contexto'} | "
            f"activacion: {template.trigger_mode} | "
            f"campos_requeridos: {', '.join(template.trigger_fields) if template.trigger_fields else 'ninguno'}"
        )
    return "Biblioteca de interactivos disponible:\n" + "\n".join(rows)


def _infer_interactive_action(
    *,
    reply_text: str,
    agent_prompt: str,
    templates: list[AiInteractiveTemplate],
) -> str | None:
    normalized_reply = _normalize_search_text(reply_text)
    normalized_prompt = _normalize_search_text(agent_prompt)
    if not normalized_reply:
        return None

    for template in templates:
        action_key = template.action_key.strip().lower()
        options = template.options if isinstance(template.options, list) else []
        option_titles = [
            _normalize_search_text(str(option.get("title") or ""))
            for option in options
            if str(option.get("title") or "").strip()
        ]
        matched_options = [
            title for title in option_titles if title and title in normalized_reply
        ]
        normalized_body = _normalize_search_text(template.body_text)
        normalized_name = _normalize_search_text(template.name)
        exact_template_match = bool(
            normalized_body and normalized_body in normalized_reply
        )
        multiple_option_match = len(matched_options) >= 2
        menu_requested_by_agent = (
            action_key.replace("_", " ") in normalized_prompt
            or (normalized_name and normalized_name in normalized_prompt)
        )
        reply_announces_menu = "opciones" in normalized_reply or "menu" in normalized_reply

        if exact_template_match or multiple_option_match:
            return action_key
        if menu_requested_by_agent and reply_announces_menu:
            return action_key
    return None


def _selected_interactive_source_action(
    *,
    templates: list[AiInteractiveTemplate],
    interactive_reply: dict | None,
) -> str | None:
    if not isinstance(interactive_reply, dict):
        return None
    reply_id = str(interactive_reply.get("id") or "").strip()
    reply_title = _normalize_search_text(str(interactive_reply.get("title") or ""))
    for template in templates:
        options = template.options if isinstance(template.options, list) else []
        for option in options:
            option_id = str(option.get("id") or "").strip()
            option_title = _normalize_search_text(str(option.get("title") or ""))
            if reply_id and option_id == reply_id:
                return template.action_key
            if reply_title and option_title == reply_title:
                return template.action_key
    return None


@dataclass
class AutoReplyResult:
    reply_text: str
    action: str | None = None
    captured_fields: dict[str, str] = field(default_factory=dict)
    product_retailer_ids: list[str] = field(default_factory=list)
    is_first_contact: bool = False


def generate_auto_reply(
    db: Session,
    *,
    company_id: UUID,
    conversation: Conversation,
    incoming_text: str,
    incoming_interactive_reply: dict | None = None,
    payment_context: str | None = None,
) -> AutoReplyResult | None:
    if getattr(conversation, "ai_enabled", True) is False:
        logger.info("AI auto-reply skipped: conversation paused company_id=%s conversation_id=%s", company_id, conversation.id)
        return None
    if _load_latest_conversation_ai_enabled(
        db,
        company_id=company_id,
        conversation_id=conversation.id,
    ) is False:
        logger.info(
            "AI auto-reply skipped after freshness check: conversation paused company_id=%s conversation_id=%s",
            company_id,
            conversation.id,
        )
        return None
    settings = get_settings()
    agent = _get_active_agent(db, company_id=company_id)
    if agent is None:
        logger.info("AI auto-reply skipped: no active agent for company_id=%s", company_id)
        return None

    rules = agent.rules if isinstance(agent.rules, dict) else {}
    if not _as_bool(rules.get("auto_reply_enabled"), default=True):
        logger.info("AI auto-reply disabled by rules for company_id=%s", company_id)
        return None

    company = db.scalar(select(Company).where(Company.id == company_id))
    company_name = company.name if company else "la empresa"
    timezone_name = company.timezone if company else None
    operational_config = build_operational_config(rules, fallback_timezone=timezone_name)
    operational_section = get_effective_operational_section(operational_config)
    hours = evaluate_business_hours(
        operational_config,
        timezone_name=timezone_name,
    )
    autonomy = operational_section.get("autonomy", {}) if isinstance(operational_section, dict) else {}
    escalation = operational_section.get("escalation", {}) if isinstance(operational_section, dict) else {}
    schedule = (
        f"{hours['day_type']} {hours['window']['start']}-{hours['window']['end']} ({hours['timezone']})"
    )
    model = str(rules.get("model") or "gpt-4o-mini")
    temperature = float(rules.get("temperature") or 0.4)
    max_tokens = int(rules.get("max_tokens") or 350)
    language = _as_text(rules.get("language"), default="espanol")
    personality = _as_text(rules.get("personality"))
    welcome_message = _as_text(rules.get("welcome_message"))
    business_description = _as_text(rules.get("business_description"))
    products_services = _as_text(rules.get("products_services"))
    conversation_objective = _as_text(
        agent.conversation_objective,
        default=_as_text(rules.get("conversation_objective")),
    )
    conversation_guide = _as_text(
        agent.conversation_guide,
        default=_as_text(rules.get("conversation_guide")),
    )
    capture_fields = _as_list(rules.get("capture_fields"))
    funnel_steps = _as_list(rules.get("funnel_steps"))
    faq_legacy = _as_text(rules.get("faq"))
    handoff_rule = _as_text(rules.get("handoff_rule"))
    knowledge_sources = _as_text(rules.get("knowledge_sources"))
    guardrails = _as_text(rules.get("guardrails"))
    security_rules = _as_text(
        agent.security_rules,
        default=_as_text(operational_section.get("security", {}).get("custom_rules"), default=guardrails),
    )
    tone = _as_text(agent.tone or rules.get("tone"), default="profesional cercano")
    funnel = None
    if conversation.funnel_id:
        funnel = db.scalar(
            select(SalesFunnel)
            .where(
                SalesFunnel.company_id == company_id,
                SalesFunnel.id == conversation.funnel_id,
            )
            .options(selectinload(SalesFunnel.steps))
        )
    funnel_name = funnel.name if funnel else ""
    funnel_assignment_criteria = _as_text(funnel.assignment_criteria if funnel else "")
    funnel_welcome_message = _as_text(funnel.welcome_message if funnel else "")
    funnel_capture_fields = list(funnel.capture_fields) if funnel and isinstance(funnel.capture_fields, list) else []
    funnel_step_names = [step.name for step in funnel.steps] if funnel and funnel.steps else []
    customer_messages = _customer_message_count(
        db,
        company_id=company_id,
        conversation_id=conversation.id,
        memory_reset_at=conversation.memory_reset_at,
        memory_reset_after_message_id=conversation.memory_reset_after_message_id,
    )
    use_welcome_on_greeting = _as_bool(
        rules.get("use_welcome_on_greeting"), default=True
    )

    first_contact = customer_messages <= 1
    greeting_message = use_welcome_on_greeting and _is_greeting(incoming_text)
    intent = classify_intent(incoming_text)
    available_action_templates = _list_active_action_templates(
        db, company_id=company_id
    )
    available_actions = [
        template.action_key for template in available_action_templates
    ]
    selected_source_action = _selected_interactive_source_action(
        templates=available_action_templates,
        interactive_reply=incoming_interactive_reply,
    )
    interactive_selection_context = (
        "Seleccion interactiva recibida en este turno:\n"
        f"- menu_origen: {selected_source_action or 'no_identificado'}\n"
        f"- opcion_id: {incoming_interactive_reply.get('id') or 'sin_id'}\n"
        f"- opcion_elegida: {incoming_interactive_reply.get('title') or incoming_text}\n"
        "- Trata la opcion elegida como la intencion actual del cliente. Responde usando el "
        "conocimiento del tenant y avanza la conversacion. No vuelvas a enviar el menu de origen "
        "en este mismo turno. Podras enviarlo de nuevo mas adelante si el cliente pide volver al menu.\n\n"
        if isinstance(incoming_interactive_reply, dict)
        else ""
    )

    critical_intents = set(_as_list(autonomy.get("critical_intents"))) or {
        "buy_product",
        "schedule_appointment",
        "request_human",
        "complaint",
    }
    required_capture_fields = {
        field.lower()
        for field in _as_list(autonomy.get("required_capture_fields"))
    }
    if not hours["within_hours"] and hours["outside_hours_behavior"] == "handoff":
        return AutoReplyResult(
            reply_text=hours["outside_hours_message"] or escalation.get("handoff_message") or "Te paso con una persona del equipo.",
            action=None,
            is_first_contact=first_contact,
        )
    if intent.intent in {"request_human", "complaint"}:
        return AutoReplyResult(
            reply_text=escalation.get("handoff_message") or "Te paso con una persona del equipo.",
            action=None,
            is_first_contact=first_contact,
        )
    if _appointment_preference_pending(
        db,
        company_id=company_id,
        conversation_id=conversation.id,
        memory_reset_at=conversation.memory_reset_at,
    ):
        return AutoReplyResult(
            reply_text="¿Prefieres mañana o tarde?",
            action=None,
            is_first_contact=first_contact,
        )
    if not settings.openai_api_key:
        logger.warning("AI auto-reply skipped: OPENAI_API_KEY is empty")
        return None

    system_prompt = (
        "Configuracion obligatoria del agente desde ai_agents. Esta seccion tiene prioridad sobre "
        "catalogo, FAQ, historial y cualquier contexto auxiliar:\n"
        f"system_prompt:\n{agent.system_prompt}\n\n"
        f"tone: {tone}\n"
        f"conversation_objective: {conversation_objective or 'resolver dudas y llevar a conversion'}\n"
        f"conversation_guide:\n{conversation_guide or 'sin guion conversacional definido'}\n"
        f"security_rules: {security_rules or faq_legacy or 'no inventar datos ni promesas no verificadas'}\n"
        f"rules_json: {_as_json_context(rules)}\n\n"
        "Contexto auxiliar del tenant. Usalo solo cuando ayude a cumplir la configuracion del agente:\n"
        f"Tenant: {company_name}\n"
        f"Idioma de respuesta: {language}\n"
        f"Personalidad: {personality or 'comercial consultiva'}\n"
        f"Horario operativo: {schedule or 'sin restriccion'}\n"
        f"Descripcion del negocio: {business_description or 'no definida'}\n"
        f"Productos/servicios declarados: {products_services or 'no definidos'}\n"
        f"Funnel activo: {funnel_name or 'sin funnel asignado'}\n"
        f"Criterio de asignacion del funnel: {funnel_assignment_criteria or 'no definido'}\n"
        f"Fuentes de conocimiento: {knowledge_sources or 'catalogo y mensajes del tenant'}\n"
        f"{_build_faq_context(db, company_id=company_id)}\n"
        f"{payment_context or _build_payment_context(db, company_id=company_id, conversation_id=conversation.id, memory_reset_at=conversation.memory_reset_at, memory_reset_after_message_id=conversation.memory_reset_after_message_id)}\n"
        "Reglas de pago vencido:\n"
        "- Si el contexto indica que un link de pago ya vencio y el seguimiento automatico ya fue enviado, no repitas el recordatorio.\n"
        "- Si el cliente quiere continuar, ofrece seguir el flujo comercial sin confirmar pagos, sin extender vencimientos y sin retener inventario.\n"
        "- Si hace falta un nuevo cobro, usa backend autorizado para generar una nueva orden o un nuevo link.\n"
        f"Campos a capturar: {', '.join(capture_fields or funnel_capture_fields) if (capture_fields or funnel_capture_fields) else 'sin campos obligatorios'}\n"
        f"Pasos del funnel: {', '.join(funnel_steps or funnel_step_names) if (funnel_steps or funnel_step_names) else 'sin pasos definidos'}\n"
        f"Criterio de handoff: {handoff_rule or 'cuando el cliente pida humano'}\n"
        f"Mensaje de bienvenida recomendado: {welcome_message or funnel_welcome_message or 'no definido'}\n"
        "Configuracion operativa publicada o de borrador segun el estado del agente:\n"
        f"{summarize_operational_config(operational_config, timezone_name=timezone_name)}\n\n"
        f"{_build_catalog_context(db, company_id=company_id)}\n\n"
        f"{_build_interactive_actions_context(available_action_templates)}\n\n"
        f"{interactive_selection_context}"
        "Reglas de salida:\n"
        "- Obedece primero system_prompt, tone, rules_json, security_rules, conversation_objective y conversation_guide.\n"
        "- Usa conversation_guide como secuencia operativa: evalua sus etapas y condiciones en cada turno. Si una etapa pide un interactivo, devuelve su action_key exacto en action.\n"
        "- Responde siempre en el idioma configurado arriba.\n"
        "- No inventes precios ni stock.\n"
        "- Antes de ofrecer o recomendar cualquier producto, consulta el catalogo e inventario interno incluido arriba.\n"
        "- Ofrece un producto solamente si su Stock real disponible es mayor que cero. Si no tiene inventario configurado o esta agotado, no lo ofrezcas y explica brevemente que una asesora confirmara disponibilidad.\n"
        "- Si no tienes dato suficiente, pide una aclaracion breve.\n"
        "- Cuando la intencion sea agendar una cita, primero pregunta si prefiere manana o tarde y no propongas horarios concretos hasta capturar esa preferencia.\n"
        "- Si aplica handoff por regla, indica transferencia a humano.\n"
        "- Mensajes cortos (maximo 4 lineas) orientados a conversion.\n"
        "- Usa el catalogo solo como fuente interna. No listes productos, precios ni catalogo completo en el saludo.\n"
        "- En primer contacto o saludo, respeta la apertura del prompt del agente y no recomiendes productos hasta que el cliente elija una opcion o pregunte por productos.\n"
        "- Si existe un funnel de bienvenida, usa su mensaje inicial, campos de captura y pasos como contexto operativo antes de responder.\n"
        "- La biblioteca de interactivos es el contrato de acciones del tenant. Cuando el prompt del agente o una regla_de_uso solicite enviar un menu, boton o lista, usa action con su action_key exacto. No redactes manualmente las opciones de esa plantilla en reply_text.\n"
        "- Interpreta frases como 'envia el interactivo menu_principal' o 'muestra la lista servicios' usando el action_key exacto disponible en la biblioteca.\n"
        "- Evalua la regla_de_uso de cada interactivo en cada turno. Si corresponde enviarlo, responde con su action_key exacto.\n"
        "- Cuando uses action, reply_text debe ser una confirmacion breve porque el backend enviara el interactivo correspondiente.\n"
        "- Cuando el cliente pida productos, detalles o una recomendacion y ya tengas contexto suficiente, usa product_retailer_ids para enviar cards nativas de WhatsApp.\n"
        "- En product_retailer_ids devuelve unicamente Meta retailer_id copiados literalmente del catalogo interno, maximo 10 y ordenados por relevancia. Nunca inventes IDs.\n"
        "- Incluye solamente productos con mapeo Meta y Stock real disponible mayor que cero. Si no corresponde enviar cards, devuelve una lista vacia.\n"
        "- Cuando uses product_retailer_ids, reply_text debe ser una introduccion comercial breve para acompañar las cards.\n"
        "- En captured_fields devuelve solo datos expresamente informados o confirmados por el cliente. Usa claves breves en minuscula, por ejemplo nombre, email y ciudad.\n"
        f"- Primer contacto detectado: {'si' if first_contact else 'no'}.\n"
        f"- Mensaje de saludo detectado: {'si' if greeting_message else 'no'}.\n"
        "- Si es primer contacto, cumple estrictamente el flujo de apertura definido en el prompt del agente.\n"
        "Devuelve SIEMPRE un JSON valido sin texto adicional con este formato:\n"
        '{"reply_text":"texto para cliente","action":"clave_o_null","captured_fields":{"nombre":"valor_confirmado"},"product_retailer_ids":["id_meta"]}\n'
        "- action debe ser null o una de estas claves exactas: "
        f"{', '.join(available_actions) if available_actions else 'sin_acciones_disponibles'}.\n"
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(
        _build_recent_conversation_context(
            db,
            company_id=company_id,
            conversation_id=conversation.id,
            memory_reset_at=conversation.memory_reset_at,
            memory_reset_after_message_id=conversation.memory_reset_after_message_id,
        )
    )
    messages.append({"role": "user", "content": incoming_text})

    payload = {
        "model": model,
        "temperature": max(0.0, min(temperature, 1.0)),
        "max_tokens": max(80, min(max_tokens, 700)),
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=25) as client:
            response = client.post(OPENAI_CHAT_COMPLETIONS_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "AI auto-reply OpenAI HTTP error company_id=%s status=%s body=%s",
            company_id,
            exc.response.status_code,
            exc.response.text[:500],
        )
        return None
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("AI auto-reply transport/parse error company_id=%s: %s", company_id, exc)
        return None

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not content:
        logger.warning("AI auto-reply empty content company_id=%s", company_id)
        return None

    try:
        parsed = json.loads(content)
        reply_text = str(parsed.get("reply_text") or "").strip()
        action_raw = parsed.get("action")
        action = str(action_raw).strip().lower() if isinstance(action_raw, str) else None
        captured_fields_raw = parsed.get("captured_fields")
        captured_fields = (
            {
                str(key).strip().lower(): str(value).strip()
                for key, value in captured_fields_raw.items()
                if str(key).strip() and str(value).strip()
            }
            if isinstance(captured_fields_raw, dict)
            else {}
        )
        product_retailer_ids = list(
            dict.fromkeys(
                str(retailer_id).strip()
                for retailer_id in parsed.get("product_retailer_ids", [])
                if str(retailer_id).strip()
            )
        )[:10] if isinstance(parsed.get("product_retailer_ids"), list) else []
        if action and action not in available_actions:
            action = None
        if not action:
            action = _infer_interactive_action(
                reply_text=reply_text,
                agent_prompt=agent.system_prompt,
                templates=available_action_templates,
            )
        if action and selected_source_action and action == selected_source_action:
            logger.info(
                "AI auto-reply suppressed repeated source action company_id=%s action=%s",
                company_id,
                action,
            )
            action = None
        if (
            intent.intent in critical_intents
            and (
                intent.confidence < float(autonomy.get("min_confidence") or 0.75)
                or not _as_bool(autonomy.get("allow_critical_actions"), default=False)
                or (required_capture_fields and not required_capture_fields.issubset(set(captured_fields)))
            )
        ):
            reply_text = (
                escalation.get("clarification_message")
                or escalation.get("handoff_message")
                or "Necesito un poco mas de informacion para ayudarte mejor."
            )
            action = None
            product_retailer_ids = []
        if first_contact and greeting_message:
            action = None
            product_retailer_ids = []
            if welcome_message or funnel_welcome_message:
                reply_text = welcome_message or funnel_welcome_message
        if reply_text:
            return AutoReplyResult(
                reply_text=reply_text,
                action=action or None,
                captured_fields=captured_fields,
                product_retailer_ids=product_retailer_ids,
                is_first_contact=first_contact,
            )
    except json.JSONDecodeError:
        logger.warning("AI auto-reply non-json output company_id=%s", company_id)

    return AutoReplyResult(reply_text=content, action=None, is_first_contact=first_contact)

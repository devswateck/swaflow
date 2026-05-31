from __future__ import annotations

import logging
import json
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.models import AiAgent, AiFaqEntry, AiInteractiveTemplate
from app.companies.models import Company
from app.conversations.models import Conversation
from app.messages.models import Message
from app.products.models import Product
from app.core.config import get_settings

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
logger = logging.getLogger(__name__)
GREETING_HINTS = {
    "hola",
    "buen dia",
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


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _is_greeting(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return normalized in GREETING_HINTS


def _customer_message_count(
    db: Session, *, company_id: UUID, conversation_id: UUID
) -> int:
    return len(
        list(
            db.scalars(
                select(Message.id).where(
                    Message.company_id == company_id,
                    Message.conversation_id == conversation_id,
                    Message.sender_type == "customer",
                    Message.content.is_not(None),
                )
            )
        )
    )


def _build_catalog_context(db: Session, *, company_id: UUID, limit: int = 20) -> str:
    products = list(
        db.scalars(
            select(Product)
            .where(Product.company_id == company_id, Product.status == "active")
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
    )
    if not products:
        return "Catalogo interno para consulta: sin productos activos."

    rows: list[str] = []
    for product in products:
        price = _stringify_price(product.price)
        sku = product.sku or "-"
        rows.append(
            f"- {product.name} | SKU: {sku} | Precio: {price} {product.currency}"
        )
    return "Catalogo interno para consulta de la IA, no lo envies completo al cliente:\n" + "\n".join(rows)


def _build_recent_conversation_context(
    db: Session, *, company_id: UUID, conversation_id: UUID, limit: int = 14
) -> list[dict[str, str]]:
    messages = list(
        db.scalars(
            select(Message)
            .where(
                Message.company_id == company_id,
                Message.conversation_id == conversation_id,
                Message.content.is_not(None),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
    )
    chat_messages: list[dict[str, str]] = []
    for message in reversed(messages):
        content = (message.content or "").strip()
        if not content:
            continue
        role = "assistant" if message.sender_type == "agent" else "user"
        chat_messages.append({"role": role, "content": content})
    return chat_messages


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


def _list_active_actions(db: Session, *, company_id: UUID) -> list[str]:
    return list(
        db.scalars(
            select(AiInteractiveTemplate.action_key).where(
                AiInteractiveTemplate.company_id == company_id,
                AiInteractiveTemplate.active.is_(True),
            )
        )
    )


@dataclass
class AutoReplyResult:
    reply_text: str
    action: str | None = None


def generate_auto_reply(
    db: Session,
    *,
    company_id: UUID,
    conversation: Conversation,
    incoming_text: str,
) -> AutoReplyResult | None:
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("AI auto-reply skipped: OPENAI_API_KEY is empty")
        return None

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
    model = str(rules.get("model") or "gpt-4o-mini")
    temperature = float(rules.get("temperature") or 0.4)
    max_tokens = int(rules.get("max_tokens") or 350)
    language = _as_text(rules.get("language"), default="espanol")
    personality = _as_text(rules.get("personality"))
    schedule = _as_text(rules.get("schedule"))
    welcome_message = _as_text(rules.get("welcome_message"))
    business_description = _as_text(rules.get("business_description"))
    products_services = _as_text(rules.get("products_services"))
    conversation_objective = _as_text(
        agent.conversation_objective,
        default=_as_text(rules.get("conversation_objective")),
    )
    capture_fields = _as_list(rules.get("capture_fields"))
    funnel_steps = _as_list(rules.get("funnel_steps"))
    faq_legacy = _as_text(rules.get("faq"))
    handoff_rule = _as_text(rules.get("handoff_rule"))
    knowledge_sources = _as_text(rules.get("knowledge_sources"))
    guardrails = _as_text(rules.get("guardrails"))
    security_rules = _as_text(agent.security_rules, default=guardrails)
    tone = _as_text(agent.tone or rules.get("tone"), default="profesional cercano")
    customer_messages = _customer_message_count(
        db, company_id=company_id, conversation_id=conversation.id
    )
    use_welcome_on_greeting = _as_bool(
        rules.get("use_welcome_on_greeting"), default=True
    )

    first_contact = customer_messages <= 1
    greeting_message = use_welcome_on_greeting and _is_greeting(incoming_text)
    available_actions = _list_active_actions(db, company_id=company_id)

    system_prompt = (
        "Configuracion obligatoria del agente desde ai_agents. Esta seccion tiene prioridad sobre "
        "catalogo, FAQ, historial y cualquier contexto auxiliar:\n"
        f"system_prompt:\n{agent.system_prompt}\n\n"
        f"tone: {tone}\n"
        f"conversation_objective: {conversation_objective or 'resolver dudas y llevar a conversion'}\n"
        f"security_rules: {security_rules or faq_legacy or 'no inventar datos ni promesas no verificadas'}\n"
        f"rules_json: {_as_json_context(rules)}\n\n"
        "Contexto auxiliar del tenant. Usalo solo cuando ayude a cumplir la configuracion del agente:\n"
        f"Tenant: {company_name}\n"
        f"Idioma de respuesta: {language}\n"
        f"Personalidad: {personality or 'comercial consultiva'}\n"
        f"Horario operativo: {schedule or 'sin restriccion'}\n"
        f"Descripcion del negocio: {business_description or 'no definida'}\n"
        f"Productos/servicios declarados: {products_services or 'no definidos'}\n"
        f"Fuentes de conocimiento: {knowledge_sources or 'catalogo y mensajes del tenant'}\n"
        f"{_build_faq_context(db, company_id=company_id)}\n"
        f"Campos a capturar: {', '.join(capture_fields) if capture_fields else 'sin campos obligatorios'}\n"
        f"Pasos del funnel: {', '.join(funnel_steps) if funnel_steps else 'sin pasos definidos'}\n"
        f"Criterio de handoff: {handoff_rule or 'cuando el cliente pida humano'}\n"
        f"Mensaje de bienvenida recomendado: {welcome_message or 'no definido'}\n"
        f"{_build_catalog_context(db, company_id=company_id)}\n\n"
        "Reglas de salida:\n"
        "- Obedece primero system_prompt, tone, rules_json, security_rules y conversation_objective.\n"
        "- Responde siempre en el idioma configurado arriba.\n"
        "- No inventes precios ni stock.\n"
        "- Si no tienes dato suficiente, pide una aclaracion breve.\n"
        "- Si aplica handoff por regla, indica transferencia a humano.\n"
        "- Mensajes cortos (maximo 4 lineas) orientados a conversion.\n"
        "- Usa el catalogo solo como fuente interna. No listes productos, precios ni catalogo completo en el saludo.\n"
        "- En primer contacto o saludo, respeta la apertura del prompt del agente y no recomiendes productos hasta que el cliente elija una opcion o pregunte por productos.\n"
        f"- Primer contacto detectado: {'si' if first_contact else 'no'}.\n"
        f"- Mensaje de saludo detectado: {'si' if greeting_message else 'no'}.\n"
        "- Si es primer contacto, cumple estrictamente el flujo de apertura definido en el prompt del agente.\n"
        "Devuelve SIEMPRE un JSON valido sin texto adicional con este formato:\n"
        '{"reply_text":"texto para cliente","action":"clave_o_null"}\n'
        "- action debe ser null o una de estas claves exactas: "
        f"{', '.join(available_actions) if available_actions else 'sin_acciones_disponibles'}.\n"
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(
        _build_recent_conversation_context(
            db, company_id=company_id, conversation_id=conversation.id
        )
    )
    messages.append({"role": "user", "content": incoming_text})

    payload = {
        "model": model,
        "temperature": max(0.0, min(temperature, 1.0)),
        "max_tokens": max(80, min(max_tokens, 700)),
        "messages": messages,
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
        action = str(action_raw).strip() if isinstance(action_raw, str) else None
        if action and action not in available_actions:
            action = None
        if reply_text:
            return AutoReplyResult(reply_text=reply_text, action=action or None)
    except json.JSONDecodeError:
        logger.warning("AI auto-reply non-json output company_id=%s", company_id)

    return AutoReplyResult(reply_text=content, action=None)

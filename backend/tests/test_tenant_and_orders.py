import json
import hashlib
import hmac
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.schemas import PasswordChangeRequest
from app.auth.service import authenticate_user, build_current_user_payload, change_own_password
from app.audit.service import list_audit_logs
from app.events.service import create_event
from app.ai.schemas import (
    AiAgentCreate,
    AiAgentUpdate,
    AiFaqEntryCreate,
    AiInteractiveTemplateCreate,
    AiInteractiveTemplateOption,
)
from app.ai.service import (
    create_agent,
    create_faq_entry,
    create_interactive_template,
    get_agent,
    get_operational_config,
    list_agents,
    list_interactive_templates,
    publish_operational_config_for_agent,
    simulate_operational_config,
    update_agent,
)
from app.companies.models import Company
from app.companies import service
from app.companies.schemas import CompanyCreate, CompanyUpdate
from app.companies.service import create_company_with_owner, update_company
from app.contacts.models import Contact
from app.appointments.schemas import (
    AppointmentCreate,
    AppointmentOperationalConfigUpdate,
    AppointmentUpdate,
)
from app.appointments.service import create_appointment, update_appointment
from app.appointments.service import get_shared_operational_config, update_shared_operational_config
from app.events.models import Event
from app.core.crypto import decrypt_secret
from app.core.schemas import OwnerCreate
from app.ai.runtime import (
    AutoReplyResult,
    _build_catalog_context,
    _infer_interactive_action,
    _selected_interactive_source_action,
    generate_auto_reply,
)
from app.ai.tools import check_stock_tool, search_products_tool
from app.ai.routes import get_default_system_prompt
from app.ai.models import AiAgent
from app.appointments.models import Appointment
from app.conversations.models import Conversation
from app.conversations.schemas import ConversationCreate
from app.conversations.service import (
    assign_conversation_funnel,
    assign_conversation,
    create_conversation,
    get_conversation,
    get_or_create_open_conversation,
    list_conversations,
    prepare_conversation_appointment_intent,
)
from app.funnels import service as funnel_service
from app.inventory.models import Inventory
from app.inventory.service import list_inventory
from app.messages.models import Message
from app.integrations.models import CompanyIntegration
from app.integrations.schemas import (
    IntegrationCreate,
    IntegrationUpdate,
    OutboundWebhookCreate,
    OutboundWebhookUpdate,
)
from app.integrations.service import (
    create_integration,
    create_outbound_webhook,
    update_integration,
    update_outbound_webhook,
)
from app.integrations.calendar import HttpCalendarAdapter, normalize_calendar_config
from app.payments.notifications import notify_order_paid
from app.payments.service import process_payment_webhook
from app.orders.schemas import OrderCreate, OrderItemCreate
from app.orders.service import cancel_order, create_order, generate_payment_link, list_orders, mark_paid_by_reference
from app.orders.models import Order
from app.funnels.models import SalesFunnel
from app.funnels.schemas import FunnelCreate, FunnelStepWrite, FunnelUpdate
from app.funnels.service import (
    create_funnel,
    ensure_welcome_funnel,
    get_default_funnel,
    get_funnel,
    update_funnel,
)
from app.products.models import Product
from app.products.service import get_product
from app.core.security import verify_password
from app.users.models import User
from app.users.schemas import UserCreate
from app.users.service import create_user, get_user
from app.inventory.schemas import InventoryAdjustment, InventoryRead, InventoryUpdate
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.schemas import WhatsAppAccountCreate
from app.whatsapp.service import (
    _build_available_products_fallback,
    _catalog_link_warning,
    _incoming_message_content,
    _interactive_reply_requests_catalog,
    _list_available_product_ids,
    _message_requests_catalog,
    _meta_inventory_quantity,
    _meta_request,
    process_webhook_payload,
    _resolve_available_product_ids,
    _resolve_configured_action,
    _should_generate_auto_reply,
    _sync_catalog_products_with_account,
    create_account,
    send_expired_payment_followup,
)
from app.inventory.service import (
    adjust_inventory,
    available_units,
    list_inventory,
    upsert_inventory,
)


def bootstrap_company(db, name: str):
    return create_company_with_owner(
        db,
        CompanyCreate(
            name=name,
            owner=OwnerCreate(
                name=f"{name} Owner",
                email=f"owner@{name.lower().replace(' ', '')}.example.com",
                password="super-secret",
            ),
        ),
    )


def bootstrap_payment_integration(
    db,
    *,
    company_id,
    provider: str = "mock",
    ttl_minutes: int = 120,
    credentials: str | None = None,
):
    payload_credentials = credentials
    if payload_credentials is None and provider == "mock":
        payload_credentials = None
    elif payload_credentials is None:
        payload_credentials = json.dumps({"private_key": f"pk_{provider}", "events_secret": f"evt_{provider}"})

    return create_integration(
        db,
        company_id=company_id,
        payload=IntegrationCreate(
            type="payments",
            credentials=payload_credentials,
            config={
                "provider": provider,
                "environment": "sandbox",
                "currency": "COP",
                "payment_link_ttl_minutes": str(ttl_minutes),
            },
        ),
    )


def sign_payment_webhook(payload: dict[str, object], secret: str) -> tuple[bytes, str]:
    raw_body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return raw_body, signature


def test_company_bootstrap_creates_owner(db):
    company, owner = bootstrap_company(db, "Acme")

    assert company.id is not None
    assert company.contact_email is None
    assert company.contact_phone is None
    assert company.currency is None
    assert company.timezone is None
    assert company.business_mode is None
    assert company.logo_url is None
    assert company.banner_url is None
    assert company.profile_url is None
    assert owner.company_id == company.id
    assert owner.role == "owner"
    assert owner.email == "owner@acme.example.com"
    assert owner.password_hash != "super-secret"
    assert verify_password("super-secret", owner.password_hash)


def test_company_bootstrap_audit_includes_owner_id(db):
    company, owner = bootstrap_company(db, "Acme")

    audit_log = list_audit_logs(db, company_id=company.id, limit=1, offset=0)[0]

    assert audit_log.action == "company.created"
    assert audit_log.metadata_json["owner_id"] == str(owner.id)
    assert audit_log.metadata_json["owner_email"] == owner.email


def test_get_default_funnel_does_not_commit(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")

    def boom(*args, **kwargs):
        raise AssertionError("get_default_funnel should not commit")

    monkeypatch.setattr(db, "commit", boom)

    funnel = get_default_funnel(db, company_id=company.id)

    assert funnel.system_key == "welcome"
    assert funnel.is_default is True


def test_company_bootstrap_rolls_back_if_welcome_funnel_bootstrap_fails(db, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("bootstrap failed")

    monkeypatch.setattr(service, "ensure_welcome_funnel", boom)

    with pytest.raises(RuntimeError, match="bootstrap failed"):
        bootstrap_company(db, "Acme")

    assert db.scalar(select(Company).where(Company.name == "Acme")) is None


def test_company_bootstrap_still_succeeds_if_audit_write_fails(db, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("audit failed")

    monkeypatch.setattr(service, "record_audit_best_effort", boom)

    company, owner = bootstrap_company(db, "Acme")

    assert company.name == "Acme"
    assert owner.email == "owner@acme.example.com"
    assert db.scalar(select(Company).where(Company.name == "Acme")) is not None
    assert db.scalar(select(User).where(User.email == "owner@acme.example.com")) is not None


def test_company_bootstrap_creates_default_welcome_funnel(db):
    company, _ = bootstrap_company(db, "Acme")

    welcome_funnel = get_default_funnel(db, company_id=company.id)

    assert welcome_funnel.company_id == company.id
    assert welcome_funnel.system_key == "welcome"
    assert welcome_funnel.is_default is True
    assert welcome_funnel.name == "Funnel de bienvenida"
    assert welcome_funnel.welcome_message
    assert welcome_funnel.capture_fields == ["Nombre", "Correo", "Ciudad"]
    assert welcome_funnel.assignment_criteria
    assert len(welcome_funnel.steps) == 3
    assert welcome_funnel.steps[0].code == "bienvenida"
    assert welcome_funnel.steps[0].config["entry_point"] is True


def test_default_welcome_funnel_is_idempotent(db):
    company, _ = bootstrap_company(db, "Acme")

    first = ensure_welcome_funnel(db, company_id=company.id)
    second = ensure_welcome_funnel(db, company_id=company.id)

    assert first.id == second.id
    assert first.system_key == "welcome"
    assert second.system_key == "welcome"
    assert len(
        list(
            db.scalars(
                select(SalesFunnel).where(
                    SalesFunnel.company_id == company.id,
                    SalesFunnel.is_default.is_(True),
                )
            )
        )
    ) == 1


def test_open_conversation_uses_default_welcome_funnel(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )
    welcome_funnel = get_default_funnel(db, company_id=company.id)

    assert conversation.funnel_id == welcome_funnel.id
    assert conversation.funnel_step_id == welcome_funnel.steps[0].id
    assert conversation.current_step == welcome_funnel.steps[0].code


def test_existing_open_conversation_backfills_default_funnel_without_internal_commit(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = Conversation(company_id=company.id, contact_id=contact.id, channel="whatsapp")
    db.add(conversation)
    db.commit()

    def boom():
        raise AssertionError("commit should not be called by get_or_create_open_conversation")

    monkeypatch.setattr(db, "commit", boom)

    updated = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )
    welcome_funnel = get_default_funnel(db, company_id=company.id)

    assert updated.id == conversation.id
    assert updated.funnel_id == welcome_funnel.id
    assert updated.funnel_step_id == welcome_funnel.steps[0].id
    assert updated.current_step == welcome_funnel.steps[0].code


def test_existing_open_conversation_repairs_inactive_welcome_funnel_on_outer_commit(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    welcome_funnel = get_default_funnel(db, company_id=company.id)
    welcome_funnel.status = "inactive"
    db.commit()

    conversation = Conversation(company_id=company.id, contact_id=contact.id, channel="whatsapp")
    db.add(conversation)
    db.commit()

    commit_calls = 0
    original_commit = db.commit

    def spy_commit():
        nonlocal commit_calls
        commit_calls += 1
        return original_commit()

    monkeypatch.setattr(db, "commit", spy_commit)

    updated = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )

    assert commit_calls == 0
    assert updated.funnel_id == welcome_funnel.id
    assert updated.current_step == welcome_funnel.steps[0].code

    monkeypatch.setattr(db, "commit", original_commit)
    db.commit()

    reloaded = db.scalar(
        select(SalesFunnel).where(
            SalesFunnel.company_id == company.id,
            SalesFunnel.id == welcome_funnel.id,
        )
    )
    assert reloaded is not None
    assert reloaded.status == "active"


def test_stale_open_conversation_is_closed_and_recreated_after_24_hours(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    stale_conversation = Conversation(company_id=company.id, contact_id=contact.id, channel="whatsapp")
    stale_conversation.last_message_at = datetime.now(UTC) - timedelta(hours=25)
    db.add(stale_conversation)
    db.commit()

    recreated = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )

    assert recreated.id != stale_conversation.id
    assert recreated.status == "open"

    closed_stale = db.scalar(
        select(Conversation).where(
            Conversation.company_id == company.id,
            Conversation.id == stale_conversation.id,
        )
    )
    assert closed_stale is not None
    assert closed_stale.status == "closed"


def test_inbox_conversations_can_filter_by_funnel(db):
    company, _ = bootstrap_company(db, "Acme")
    first_contact = Contact(company_id=company.id, name="Cliente 1", phone="+573001112233")
    second_contact = Contact(company_id=company.id, name="Cliente 2", phone="+573001112234")
    db.add_all([first_contact, second_contact])
    db.commit()

    custom_funnel = create_funnel(
        db,
        company_id=company.id,
        payload=FunnelCreate(
            name="Funnel VIP",
            description="Atencion prioritaria",
            status="active",
            is_default=False,
            welcome_message="Hola, cuentame tu caso.",
            capture_fields=["Nombre"],
            assignment_criteria="Clientes VIP",
            steps=[
                FunnelStepWrite(
                    position=1,
                    name="Recepcion",
                    code="recepcion",
                    prompt="Recibe al cliente VIP",
                    objectives=["Recibir"],
                    transition_criteria="El cliente comparte su necesidad",
                    status="active",
                    config={},
                )
            ],
        ),
    )
    first_conversation = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=first_contact.id,
        channel="whatsapp",
    )
    second_conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=second_contact.id, channel="whatsapp"),
    )
    assign_conversation_funnel(
        db,
        company_id=company.id,
        conversation_id=second_conversation.id,
        funnel_id=custom_funnel.id,
        funnel_step_id=custom_funnel.steps[0].id,
        current_step=custom_funnel.steps[0].code,
    )

    filtered = list_conversations(
        db,
        company_id=company.id,
        limit=50,
        offset=0,
        funnel_id=custom_funnel.id,
    )

    assert [conversation.id for conversation in filtered] == [second_conversation.id]
    assert first_conversation.id not in {conversation.id for conversation in filtered}


def test_conversation_service_returns_spanish_errors_for_missing_resources(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()
    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_conversation(db, company_id=company.id, conversation_id=uuid4())
    assert exc_info.value.status_code == 404
    assert "no encontrada" in str(exc_info.value.detail).lower()

    with pytest.raises(HTTPException) as exc_info:
        assign_conversation(
            db,
            company_id=company.id,
            conversation_id=conversation.id,
            assigned_user_id=uuid4(),
        )
    assert exc_info.value.status_code == 404
    assert "usuario no encontrado" in str(exc_info.value.detail).lower()

    with pytest.raises(HTTPException) as exc_info:
        assign_conversation_funnel(
            db,
            company_id=company.id,
            conversation_id=conversation.id,
            funnel_id=uuid4(),
            funnel_step_id=None,
            current_step=None,
        )
    assert exc_info.value.status_code == 404
    assert "funnel no encontrado" in str(exc_info.value.detail).lower()


def test_assign_conversation_funnel_returns_spanish_error_for_invalid_step(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()
    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    welcome_funnel = get_default_funnel(db, company_id=company.id)

    with pytest.raises(HTTPException) as exc_info:
        assign_conversation_funnel(
            db,
            company_id=company.id,
            conversation_id=conversation.id,
            funnel_id=welcome_funnel.id,
            funnel_step_id=uuid4(),
            current_step=None,
        )

    assert exc_info.value.status_code == 404
    assert "paso del funnel no encontrado" in str(exc_info.value.detail).lower()


def test_generate_auto_reply_uses_welcome_funnel_context(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()
    conversation = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )
    db.add(
        AiAgent(
            company_id=company.id,
            name="Agente comercial",
            system_prompt="Saluda y captura datos.",
            conversation_objective="Vender con claridad",
            conversation_guide="1. Saluda 2. Captura datos 3. Clasifica",
            security_rules="No inventar datos.",
            tone="amable",
            rules={"auto_reply_enabled": True},
            active=True,
        )
    )
    db.commit()

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"reply_text":"Hola, te ayudo con tu caso.","action":null,"captured_fields":{},"product_retailer_ids":[]}'
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None, headers=None):
            captured["payload"] = json or {}
            return FakeResponse()

    monkeypatch.setattr("app.ai.runtime.get_settings", lambda: SimpleNamespace(openai_api_key="test-key"))
    monkeypatch.setattr(
        "app.ai.runtime.evaluate_business_hours",
        lambda *args, **kwargs: {
            "timezone": "America/Bogota",
            "day_type": "weekday",
            "within_hours": True,
            "window": {"start": "08:00", "end": "18:00"},
            "outside_hours_behavior": "handoff",
            "outside_hours_message": "Estamos fuera de horario.",
            "handoff_message": "Te paso con un humano.",
            "current_iso": "2026-06-25T10:00:00-05:00",
        },
    )
    monkeypatch.setattr("app.ai.runtime.httpx.Client", FakeClient)

    result = generate_auto_reply(
        db,
        company_id=company.id,
        conversation=conversation,
        incoming_text="Necesito ayuda con mi pedido",
    )

    assert result is not None
    assert result.reply_text == "Hola, te ayudo con tu caso."
    system_prompt = captured["payload"]["messages"][0]["content"]
    assert "Funnel de bienvenida" in system_prompt
    assert "Nombre, Correo, Ciudad" in system_prompt
    assert "bienvenida" in system_prompt


def test_generate_auto_reply_asks_for_preference_before_slots(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()
    conversation = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )
    db.add(
        AiAgent(
            company_id=company.id,
            name="Agente comercial",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda 2. Ayuda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            active=True,
        )
    )
    db.commit()

    prepare_conversation_appointment_intent(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
    )

    monkeypatch.setattr("app.ai.runtime.get_settings", lambda: SimpleNamespace(openai_api_key="test-key"))
    monkeypatch.setattr(
        "app.ai.runtime.evaluate_business_hours",
        lambda *args, **kwargs: {
            "timezone": "America/Bogota",
            "day_type": "weekday",
            "within_hours": True,
            "window": {"start": "08:00", "end": "18:00"},
            "outside_hours_behavior": "normal",
            "outside_hours_message": "",
            "handoff_message": "Te paso con un humano.",
            "current_iso": "2026-06-25T10:00:00-05:00",
        },
    )

    result = generate_auto_reply(
        db,
        company_id=company.id,
        conversation=conversation,
        incoming_text="Quiero agendar",
    )

    assert result is not None
    assert result.reply_text == "¿Prefieres mañana o tarde?"


def test_generate_auto_reply_prefers_handoff_over_appointment_preference(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()
    conversation = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )
    db.add(
        AiAgent(
            company_id=company.id,
            name="Agente comercial",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda 2. Ayuda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            active=True,
        )
    )
    db.commit()

    prepare_conversation_appointment_intent(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
    )

    monkeypatch.setattr("app.ai.runtime.get_settings", lambda: SimpleNamespace(openai_api_key="test-key"))
    monkeypatch.setattr(
        "app.ai.runtime.evaluate_business_hours",
        lambda *args, **kwargs: {
            "timezone": "America/Bogota",
            "day_type": "weekday",
            "within_hours": True,
            "window": {"start": "08:00", "end": "18:00"},
            "outside_hours_behavior": "normal",
            "outside_hours_message": "",
            "handoff_message": "Te paso con un humano.",
            "current_iso": "2026-06-25T10:00:00-05:00",
        },
    )
    monkeypatch.setattr(
        "app.ai.runtime.classify_intent",
        lambda message: SimpleNamespace(intent="request_human", confidence=1.0, entities={}),
    )

    result = generate_auto_reply(
        db,
        company_id=company.id,
        conversation=conversation,
        incoming_text="Quiero hablar con una persona",
    )

    assert result is not None
    assert result.reply_text == "Te paso con una persona del equipo para continuar."


def test_generate_auto_reply_rechecks_fresh_ai_state_before_reply(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()
    conversation = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )

    monkeypatch.setattr(
        "app.ai.runtime._load_latest_conversation_ai_enabled",
        lambda *args, **kwargs: False,
    )

    result = generate_auto_reply(
        db,
        company_id=company.id,
        conversation=conversation,
        incoming_text="Quiero seguir",
    )

    assert result is None


def test_ai_agent_configuration_remains_canonical_per_tenant(db):
    company, _ = bootstrap_company(db, "Acme")

    created = create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente comercial",
            system_prompt="Prompt base de ventas.",
            conversation_objective="Acompanar ventas y consultas.",
            conversation_guide="1. Saluda 2. Detecta necesidad 3. Orienta.",
            security_rules="No inventar precios.",
            tone="cercano",
            rules={"auto_reply_enabled": True, "business_context": "Venta minorista"},
            active=True,
        ),
    )
    recreated = create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente comercial actualizado",
            system_prompt="Prompt base ajustado.",
            conversation_objective="Acompanamiento comercial completo.",
            conversation_guide="1. Saluda 2. Captura contexto 3. Ofrece siguiente paso.",
            security_rules="No inventar precios ni stock.",
            tone="consultivo",
            rules={
                "auto_reply_enabled": True,
                "business_context": "Venta minorista",
                "capture_fields": ["nombre", "correo"],
            },
            active=False,
        ),
    )
    updated = update_agent(
        db,
        company_id=company.id,
        agent_id=created.id,
        payload=AiAgentUpdate(
            name="Agente comercial final",
            system_prompt="Prompt base final.",
            conversation_objective="Cerrar oportunidades.",
            conversation_guide="1. Saluda 2. Resuelve 3. Deriva si aplica.",
            security_rules="No inventar precios ni stock.",
            tone="profesional cercano",
            rules={
                "auto_reply_enabled": False,
                "business_context": "Venta minorista",
                "capture_fields": ["nombre", "correo", "ciudad"],
            },
            active=True,
        ),
    )
    rows = list_agents(db, company_id=company.id)

    assert recreated.id == created.id
    assert updated.id == created.id
    assert len(rows) == 1
    assert rows[0].id == created.id
    assert rows[0].name == "Agente comercial final"
    assert rows[0].system_prompt == "Prompt base final."
    assert rows[0].conversation_objective == "Cerrar oportunidades."
    assert rows[0].conversation_guide == "1. Saluda 2. Resuelve 3. Deriva si aplica."
    assert rows[0].security_rules == "No inventar precios ni stock."
    assert rows[0].tone == "profesional cercano"
    assert rows[0].rules["capture_fields"] == ["nombre", "correo", "ciudad"]


def test_ai_agent_company_scope_is_unique_in_database(db):
    company, _ = bootstrap_company(db, "Acme")

    db.add_all(
        [
            AiAgent(
                company_id=company.id,
                name="Agente 1",
                system_prompt="Prompt 1",
                conversation_objective="Objetivo 1",
                conversation_guide="Guia 1",
                security_rules="Regla 1",
                tone="cercano",
                rules={},
                active=True,
            ),
            AiAgent(
                company_id=company.id,
                name="Agente 2",
                system_prompt="Prompt 2",
                conversation_objective="Objetivo 2",
                conversation_guide="Guia 2",
                security_rules="Regla 2",
                tone="profesional",
                rules={},
                active=False,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db.commit()


def test_ai_agent_config_is_tenant_scoped_and_returns_404_for_other_tenant(db):
    company_a, _ = bootstrap_company(db, "Acme")
    company_b, _ = bootstrap_company(db, "Bravo")

    created = create_agent(
        db,
        company_id=company_a.id,
        payload=AiAgentCreate(
            name="Agente Acme",
            system_prompt="Prompt Acme.",
            conversation_objective="Atender clientes de Acme.",
            conversation_guide="1. Saluda 2. Captura datos.",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            active=True,
        ),
    )

    assert list_agents(db, company_id=company_b.id) == []

    with pytest.raises(HTTPException) as exc_info:
        get_agent(db, company_id=company_b.id, agent_id=created.id)
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        update_agent(
            db,
            company_id=company_b.id,
            agent_id=created.id,
            payload=AiAgentUpdate(name="Intruso"),
        )
    assert exc_info.value.status_code == 404


def test_default_system_prompt_is_exposed_from_backend_contract():
    response = get_default_system_prompt()

    assert "No inventes precios." in response.default_system_prompt
    assert "No inventes disponibilidad." in response.default_system_prompt


def test_ai_runtime_prompt_includes_agent_faq_and_interactive_context(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()
    conversation = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )

    create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente comercial",
            system_prompt="Prompt base de ventas para Acme.",
            conversation_objective="Responder y convertir leads.",
            conversation_guide="1. Saluda 2. Detecta necesidad 3. Ofrece siguiente paso.",
            security_rules="No inventar precios ni stock.",
            tone="cercano",
            rules={
                "auto_reply_enabled": True,
                "model": "gpt-4o-mini",
                "language": "espanol",
            },
            active=True,
        ),
    )
    create_faq_entry(
        db,
        company_id=company.id,
        payload=AiFaqEntryCreate(
            question="Horarios",
            answer="Atendemos de lunes a viernes de 8 a 6.",
            active=True,
        ),
    )
    create_interactive_template(
        db,
        company_id=company.id,
        payload=AiInteractiveTemplateCreate(
            name="Menu principal",
            action_key="menu_principal",
            body_text="Selecciona una opcion",
            options=[AiInteractiveTemplateOption(id="menu_principal_opt_1", title="Productos")],
            usage_instruction="Enviar despues de capturar datos.",
            trigger_mode="after_capture",
            trigger_fields=["nombre", "correo", "ciudad"],
        ),
    )

    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"reply_text":"Hola, te ayudo con tu caso.","action":null,"captured_fields":{},"product_retailer_ids":[]}'
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None, headers=None):
            captured["payload"] = json or {}
            return FakeResponse()

    monkeypatch.setattr("app.ai.runtime.get_settings", lambda: SimpleNamespace(openai_api_key="test-key"))
    monkeypatch.setattr(
        "app.ai.runtime.evaluate_business_hours",
        lambda *args, **kwargs: {
            "timezone": "America/Bogota",
            "day_type": "weekday",
            "within_hours": True,
            "window": {"start": "08:00", "end": "18:00"},
            "outside_hours_behavior": "handoff",
            "outside_hours_message": "Estamos fuera de horario.",
            "handoff_message": "Te paso con un humano.",
            "current_iso": "2026-06-25T10:00:00-05:00",
        },
    )
    monkeypatch.setattr("app.ai.runtime.httpx.Client", FakeClient)

    result = generate_auto_reply(
        db,
        company_id=company.id,
        conversation=conversation,
        incoming_text="Necesito ayuda con mi pedido",
    )

    assert result is not None
    assert result.reply_text == "Hola, te ayudo con tu caso."
    system_prompt = str(captured["payload"]["messages"][0]["content"])
    assert "system_prompt:\nPrompt base de ventas para Acme." in system_prompt
    assert "conversation_objective: Responder y convertir leads." in system_prompt
    assert "conversation_guide:\n1. Saluda 2. Detecta necesidad 3. Ofrece siguiente paso." in system_prompt
    assert "security_rules: No inventar precios ni stock." in system_prompt
    assert "FAQ base:\n- Q: Horarios" in system_prompt
    assert "Atendemos de lunes a viernes de 8 a 6." in system_prompt
    assert "Biblioteca de interactivos disponible:" in system_prompt
    assert "menu_principal" in system_prompt
    assert "Enviar despues de capturar datos." in system_prompt
    assert "primero pregunta si prefiere manana o tarde" in system_prompt
    assert "No inventes precios ni stock." in system_prompt


def test_ai_operational_config_roundtrip_and_publish(db):
    company, _ = bootstrap_company(db, "Acme")
    operational_config = {
        "status": "draft",
        "version": 1,
        "published_at": None,
        "draft": {
            "security": {
                "mandatory_guardrails": {
                    "tenant_isolation": True,
                    "payments_locked_to_backend": True,
                    "inventory_reserved_by_backend": True,
                    "no_invention": True,
                    "no_manual_payment_confirmation": True,
                },
                "custom_rules": "No inventar disponibilidad.",
            },
            "schedule": {
                "timezone": "America/Bogota",
                "weekday": {"start": "09:00", "end": "17:00"},
                "weekend": {"start": "10:00", "end": "13:00"},
                "outside_hours_behavior": "handoff",
                "inside_hours_behavior": "normal",
                "outside_hours_message": "Fuera de horario.",
                "handoff_message": "Derivando a humano.",
            },
            "autonomy": {
                "allow_critical_actions": False,
                "critical_intents": ["buy_product", "schedule_appointment"],
                "min_confidence": "0.82",
                "required_capture_fields": ["nombre", "correo"],
            },
            "escalation": {
                "low_confidence": True,
                "complaint": True,
                "payment_failed": True,
                "stock_uncertain": True,
                "explicit_human_request": True,
                "handoff_message": "Derivando a humano.",
                "clarification_message": "Necesito mas datos.",
            },
            "policies": {
                "shipping": "Envio 48h.",
                "warranty": "Garantia 6 meses.",
                "returns": "Cambios en 7 dias.",
                "payments": "Transferencia y tarjeta.",
            },
            "priorities": {
                "priority_categories": ["premium"],
                "restricted_categories": ["adultos"],
            },
            "test_mode": {"enabled": True, "simulation_note": "Simulacion interna."},
        },
    }

    created = create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente operativo",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda 2. Ayuda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            operational_config=operational_config,
            active=True,
        ),
    )

    config = get_operational_config(db, company_id=company.id, agent_id=created.id)
    assert config.status == "draft"
    assert config.draft["schedule"]["weekday"]["start"] == "09:00"
    assert config.draft["security"]["mandatory_guardrails"]["no_invention"] is True

    published = publish_operational_config_for_agent(db, company_id=company.id, agent_id=created.id)
    reloaded = get_operational_config(db, company_id=company.id, agent_id=published.id)

    assert reloaded.status == "published"
    assert reloaded.version == 2
    assert reloaded.published["schedule"]["weekday"]["end"] == "17:00"
    assert reloaded.published["escalation"]["handoff_message"] == "Derivando a humano."


def test_shared_operational_config_roundtrip_preserves_default_duration(db):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente operativo",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            operational_config={
                "draft": {
                    "security": {
                        "mandatory_guardrails": {
                            "tenant_isolation": True,
                            "payments_locked_to_backend": True,
                            "inventory_reserved_by_backend": True,
                            "no_invention": True,
                            "no_manual_payment_confirmation": True,
                        },
                        "custom_rules": "No compartir guardrails.",
                    },
                    "schedule": {
                        "timezone": "America/Bogota",
                        "weekday": {"start": "09:00", "end": "17:00"},
                        "weekend": {"start": "10:00", "end": "13:00"},
                        "default_appointment_duration_minutes": 45,
                    }
                }
            },
            active=True,
        ),
    )

    config = get_shared_operational_config(db, company_id=company.id)
    assert config.draft.default_appointment_duration_minutes == 45
    assert config.draft.timezone == "America/Bogota"
    assert "security" not in config.model_dump()["draft"]

    updated = update_shared_operational_config(
        db,
        company_id=company.id,
        payload=AppointmentOperationalConfigUpdate(
            status="draft",
            version=config.version,
            published_at=None,
            draft={
                **config.draft.model_dump(),
                "default_appointment_duration_minutes": 30,
            },
            published=config.draft.model_dump(),
        ),
        actor_user=None,
    )

    assert updated.version == config.version + 1
    assert updated.draft.default_appointment_duration_minutes == 30
    reloaded = get_shared_operational_config(db, company_id=company.id)
    assert reloaded.version == updated.version
    assert reloaded.draft.default_appointment_duration_minutes == 30
    reloaded_agent = get_agent(db, company_id=company.id, agent_id=agent.id)
    assert reloaded_agent.rules["operational"]["draft"]["schedule"]["default_appointment_duration_minutes"] == 30
    assert reloaded_agent.rules["operational"]["draft"]["security"]["custom_rules"] == "No compartir guardrails."
    assert reloaded_agent.rules["operational"]["draft"]["security"]["mandatory_guardrails"]["no_invention"] is True


def test_shared_operational_config_works_when_agent_is_inactive(db):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente operativo",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            operational_config={
                "draft": {
                    "schedule": {
                        "timezone": "America/Bogota",
                        "weekday": {"start": "09:00", "end": "17:00"},
                        "weekend": {"start": "10:00", "end": "13:00"},
                        "default_appointment_duration_minutes": 45,
                    }
                }
            },
            active=False,
        ),
    )

    config = get_shared_operational_config(db, company_id=company.id)
    assert config.draft.default_appointment_duration_minutes == 45

    updated = update_shared_operational_config(
        db,
        company_id=company.id,
        payload=AppointmentOperationalConfigUpdate(
            status="draft",
            version=config.version,
            published_at=None,
            draft={
                **config.draft.model_dump(),
                "default_appointment_duration_minutes": 30,
            },
            published=config.draft.model_dump(),
        ),
        actor_user=None,
    )

    assert updated.draft.default_appointment_duration_minutes == 30
    assert updated.published.default_appointment_duration_minutes == 45


def test_ai_operational_config_rejects_guardrail_disable(db):
    company, _ = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc_info:
        create_agent(
            db,
            company_id=company.id,
            payload=AiAgentCreate(
                name="Agente inseguro",
                system_prompt="Prompt base.",
                conversation_objective="Responder.",
                conversation_guide="1. Saluda",
                security_rules="No inventar datos.",
                tone="cercano",
                rules={"auto_reply_enabled": True},
                operational_config={
                    "draft": {
                        "security": {
                            "mandatory_guardrails": {
                                "tenant_isolation": False,
                                "payments_locked_to_backend": True,
                                "inventory_reserved_by_backend": True,
                                "no_invention": True,
                                "no_manual_payment_confirmation": True,
                            },
                            "custom_rules": "",
                        }
                    }
                },
                active=True,
            ),
        )

    assert exc_info.value.status_code == 422
    assert "guardrails obligatorios" in str(exc_info.value.detail).lower()


def test_generate_auto_reply_hands_off_outside_business_hours(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()
    conversation = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )
    create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente operativo",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            operational_config={
                "draft": {
                    "schedule": {
                        "timezone": "America/Bogota",
                        "weekday": {"start": "09:00", "end": "17:00"},
                        "weekend": {"start": "09:00", "end": "13:00"},
                        "outside_hours_behavior": "handoff",
                        "outside_hours_message": "Estamos fuera de horario.",
                        "handoff_message": "Te paso con un humano.",
                    }
                }
            },
            active=True,
        ),
    )

    monkeypatch.setattr("app.ai.runtime.get_settings", lambda: SimpleNamespace(openai_api_key="test-key"))
    monkeypatch.setattr(
        "app.ai.runtime.evaluate_business_hours",
        lambda *args, **kwargs: {
            "timezone": "America/Bogota",
            "day_type": "weekday",
            "within_hours": False,
            "window": {"start": "09:00", "end": "17:00"},
            "outside_hours_behavior": "handoff",
            "outside_hours_message": "Estamos fuera de horario.",
            "handoff_message": "Te paso con un humano.",
            "current_iso": "2026-06-25T22:00:00-05:00",
        },
    )

    result = generate_auto_reply(
        db,
        company_id=company.id,
        conversation=conversation,
        incoming_text="Hola",
    )

    assert result is not None
    assert result.reply_text == "Estamos fuera de horario."
    assert result.action is None


def test_generate_auto_reply_escalates_low_confidence_critical_intent(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()
    conversation = get_or_create_open_conversation(
        db,
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
    )
    create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente operativo",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            operational_config={
                "draft": {
                    "autonomy": {
                        "allow_critical_actions": False,
                        "critical_intents": ["buy_product", "schedule_appointment"],
                        "min_confidence": "0.95",
                        "required_capture_fields": ["nombre", "correo"],
                    },
                    "escalation": {
                        "low_confidence": True,
                        "complaint": True,
                        "payment_failed": True,
                        "stock_uncertain": True,
                        "explicit_human_request": True,
                        "handoff_message": "Te paso con un humano.",
                        "clarification_message": "Necesito confirmar algunos datos antes de avanzar.",
                    },
                }
            },
            active=True,
        ),
    )

    monkeypatch.setattr("app.ai.runtime.get_settings", lambda: SimpleNamespace(openai_api_key="test-key"))
    monkeypatch.setattr(
        "app.ai.runtime.evaluate_business_hours",
        lambda *args, **kwargs: {
            "timezone": "America/Bogota",
            "day_type": "weekday",
            "within_hours": True,
            "window": {"start": "09:00", "end": "17:00"},
            "outside_hours_behavior": "handoff",
            "outside_hours_message": "Estamos fuera de horario.",
            "handoff_message": "Te paso con un humano.",
            "current_iso": "2026-06-25T10:00:00-05:00",
        },
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"reply_text":"Claro, te ayudo con la compra.","action":"menu_principal","captured_fields":{"nombre":"Ana"},"product_retailer_ids":["ret-1"]}'
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.ai.runtime.httpx.Client", FakeClient)

    result = generate_auto_reply(
        db,
        company_id=company.id,
        conversation=conversation,
        incoming_text="Quiero comprar",
    )

    assert result is not None
    assert result.reply_text == "Necesito confirmar algunos datos antes de avanzar."
    assert result.action is None
    assert result.product_retailer_ids == []


def test_operational_config_simulation_reports_handoff(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    agent = create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente operativo",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            operational_config={
                "draft": {
                    "schedule": {
                        "timezone": "America/Bogota",
                        "weekday": {"start": "09:00", "end": "17:00"},
                        "weekend": {"start": "09:00", "end": "13:00"},
                        "outside_hours_behavior": "handoff",
                        "outside_hours_message": "Estamos fuera de horario.",
                        "handoff_message": "Te paso con un humano.",
                    },
                    "autonomy": {
                        "allow_critical_actions": False,
                        "critical_intents": ["buy_product"],
                        "min_confidence": "0.95",
                        "required_capture_fields": ["nombre"],
                    },
                }
            },
            active=True,
        ),
    )

    monkeypatch.setattr(
        "app.ai.operational.evaluate_business_hours",
        lambda *args, **kwargs: {
            "timezone": "America/Bogota",
            "day_type": "weekday",
            "within_hours": False,
            "window": {"start": "09:00", "end": "17:00"},
            "outside_hours_behavior": "handoff",
            "outside_hours_message": "Estamos fuera de horario.",
            "handoff_message": "Te paso con un humano.",
            "current_iso": "2026-06-25T22:00:00-05:00",
        },
    )

    simulation = simulate_operational_config(
        db,
        company_id=company.id,
        agent_id=agent.id,
        message="Quiero comprar",
    )

    assert simulation.within_hours is False
    assert simulation.requires_handoff is True
    assert simulation.reason == "fuera de horario"
    assert simulation.suggested_reply == "Estamos fuera de horario."


def test_operational_config_simulation_uses_preview_payload(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente operativo",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            operational_config={
                "draft": {
                    "schedule": {
                        "timezone": "America/Bogota",
                        "weekday": {"start": "00:00", "end": "23:59"},
                        "weekend": {"start": "09:00", "end": "13:00"},
                        "outside_hours_behavior": "auto_reply",
                        "outside_hours_message": "Estamos fuera de horario.",
                        "handoff_message": "Te paso con un humano.",
                    },
                    "autonomy": {
                        "allow_critical_actions": False,
                        "critical_intents": ["buy_product"],
                        "min_confidence": "0.95",
                        "required_capture_fields": ["nombre"],
                    },
                }
            },
            active=True,
        ),
    )

    def fake_evaluate_business_hours(operational_config, *, timezone_name, now=None):
        section = operational_config.get("draft") if isinstance(operational_config, dict) else {}
        schedule = section.get("schedule") if isinstance(section, dict) else {}
        weekday = schedule.get("weekday") if isinstance(schedule, dict) else {}
        is_preview = weekday.get("start") == "09:00"
        return {
            "timezone": timezone_name or "America/Bogota",
            "day_type": "weekday",
            "within_hours": not is_preview,
            "window": {"start": "09:00", "end": "17:00"},
            "outside_hours_behavior": "handoff" if is_preview else "auto_reply",
            "outside_hours_message": "Estamos fuera de horario.",
            "handoff_message": "Te paso con un humano.",
            "current_iso": "2026-06-25T10:00:00-05:00",
        }

    monkeypatch.setattr("app.ai.operational.evaluate_business_hours", fake_evaluate_business_hours)

    saved_simulation = simulate_operational_config(
        db,
        company_id=company.id,
        agent_id=agent.id,
        message="Hola",
    )
    preview_simulation = simulate_operational_config(
        db,
        company_id=company.id,
        agent_id=agent.id,
        message="Hola",
        operational_config={
            "draft": {
                "schedule": {
                    "timezone": "America/Bogota",
                    "weekday": {"start": "09:00", "end": "17:00"},
                    "weekend": {"start": "09:00", "end": "13:00"},
                    "outside_hours_behavior": "handoff",
                    "outside_hours_message": "Estamos fuera de horario.",
                    "handoff_message": "Te paso con un humano.",
                },
                "autonomy": {
                    "allow_critical_actions": False,
                    "critical_intents": ["buy_product"],
                    "min_confidence": "0.95",
                    "required_capture_fields": ["nombre"],
                },
            }
        },
    )

    assert saved_simulation.status == "draft"
    assert preview_simulation.status == "draft"
    assert saved_simulation.within_hours is True
    assert saved_simulation.requires_handoff is False
    assert preview_simulation.within_hours is False
    assert preview_simulation.requires_handoff is True


def test_operational_config_simulation_rejects_invalid_preview_guardrails(db):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente operativo",
            system_prompt="Prompt base.",
            conversation_objective="Responder.",
            conversation_guide="1. Saluda",
            security_rules="No inventar datos.",
            tone="cercano",
            rules={"auto_reply_enabled": True},
            operational_config={
                "draft": {
                    "schedule": {
                        "timezone": "America/Bogota",
                        "weekday": {"start": "09:00", "end": "17:00"},
                        "weekend": {"start": "09:00", "end": "13:00"},
                        "outside_hours_behavior": "handoff",
                        "outside_hours_message": "Estamos fuera de horario.",
                        "handoff_message": "Te paso con un humano.",
                    }
                }
            },
            active=True,
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        simulate_operational_config(
            db,
            company_id=company.id,
            agent_id=agent.id,
            message="Hola",
            operational_config={
                "draft": {
                    "security": {
                        "mandatory_guardrails": {
                            "tenant_isolation": False,
                            "payments_locked_to_backend": True,
                            "inventory_reserved_by_backend": True,
                            "no_invention": True,
                            "no_manual_payment_confirmation": True,
                        }
                    }
                }
            },
        )

    assert exc_info.value.status_code == 422


def test_funnel_configuration_persists_welcome_fields_and_steps(db):
    company, _ = bootstrap_company(db, "Acme")

    funnel = create_funnel(
        db,
        company_id=company.id,
        payload=FunnelCreate(
            name="Funnel de soporte",
            description="Flujo para tickets y seguimiento.",
            status="active",
            is_default=False,
            welcome_message="Hola, cuéntame tu caso.",
            capture_fields=["Nombre", "Correo"],
            assignment_criteria="Casos de soporte o reclamo",
            steps=[
                FunnelStepWrite(
                    position=1,
                    name="Escucha",
                    code="escucha",
                    prompt="Recibe el caso y resume el problema.",
                    objectives=["Entender el problema"],
                    transition_criteria="El cliente explica el motivo",
                    status="active",
                    config={"handoff": "support"},
                )
            ],
        ),
    )

    assert funnel.welcome_message == "Hola, cuéntame tu caso."
    assert funnel.capture_fields == ["Nombre", "Correo"]
    assert funnel.assignment_criteria == "Casos de soporte o reclamo"
    assert funnel.steps[0].objectives == ["Entender el problema"]
    assert funnel.steps[0].config == {"handoff": "support"}


def test_welcome_funnel_cannot_be_unset_as_default(db):
    company, _ = bootstrap_company(db, "Acme")
    welcome_funnel = get_default_funnel(db, company_id=company.id)

    renamed = update_funnel(
        db,
        company_id=company.id,
        funnel_id=welcome_funnel.id,
        payload=FunnelUpdate(name="Funnel VIP"),
    )

    assert renamed.id == welcome_funnel.id
    assert renamed.system_key == "welcome"
    assert renamed.name == "Funnel VIP"

    with pytest.raises(HTTPException) as exc_info:
        update_funnel(
            db,
            company_id=company.id,
            funnel_id=renamed.id,
            payload=FunnelUpdate(is_default=False),
        )

    assert exc_info.value.status_code == 422
    assert "bienvenida" in str(exc_info.value.detail).lower()
    reloaded = get_default_funnel(db, company_id=company.id)
    assert reloaded.id == renamed.id
    assert reloaded.is_default is True


def test_welcome_funnel_cannot_be_set_inactive(db):
    company, _ = bootstrap_company(db, "Acme")
    welcome_funnel = get_default_funnel(db, company_id=company.id)

    with pytest.raises(HTTPException) as exc_info:
        update_funnel(
            db,
            company_id=company.id,
            funnel_id=welcome_funnel.id,
            payload=FunnelUpdate(status="inactive"),
    )

    assert exc_info.value.status_code == 422
    assert "debe permanecer activo" in str(exc_info.value.detail).lower()


def test_welcome_funnel_cannot_be_deleted(db):
    company, _ = bootstrap_company(db, "Acme")
    welcome_funnel = get_default_funnel(db, company_id=company.id)

    with pytest.raises(HTTPException) as exc_info:
        funnel_service.delete_funnel(db, company_id=company.id, funnel_id=welcome_funnel.id)

    assert exc_info.value.status_code == 422
    assert "funnel de bienvenida" in str(exc_info.value.detail).lower()
    reloaded = get_default_funnel(db, company_id=company.id)
    assert reloaded.id == welcome_funnel.id


def test_custom_funnel_cannot_be_marked_as_default(db):
    company, _ = bootstrap_company(db, "Acme")
    welcome_funnel = get_default_funnel(db, company_id=company.id)
    custom_funnel = create_funnel(
        db,
        company_id=company.id,
        payload=FunnelCreate(
            name="Funnel de soporte",
            description="Flujo para tickets y seguimiento.",
            status="active",
            is_default=False,
            welcome_message="Hola, cuéntame tu caso.",
            capture_fields=["Nombre", "Correo"],
            assignment_criteria="Casos de soporte o reclamo",
            steps=[
                FunnelStepWrite(
                    position=1,
                    name="Escucha",
                    code="escucha",
                    prompt="Recibe el caso y resume el problema.",
                    objectives=["Entender el problema"],
                    transition_criteria="El cliente explica el motivo",
                    status="active",
                    config={"handoff": "support"},
                )
            ],
        ),
    )

    assert welcome_funnel.system_key == "welcome"
    assert custom_funnel.system_key is None

    with pytest.raises(HTTPException) as exc_info:
        update_funnel(
            db,
            company_id=company.id,
            funnel_id=custom_funnel.id,
            payload=FunnelUpdate(is_default=True),
        )

    assert exc_info.value.status_code == 422
    assert "bienvenida" in str(exc_info.value.detail).lower() or "predeterminado" in str(
        exc_info.value.detail
    ).lower()


def test_legacy_renamed_welcome_funnel_is_repaired_without_duplication(db):
    company, _ = bootstrap_company(db, "Acme")
    welcome_funnel = get_default_funnel(db, company_id=company.id)

    renamed = update_funnel(
        db,
        company_id=company.id,
        funnel_id=welcome_funnel.id,
        payload=FunnelUpdate(name="Funnel VIP"),
    )
    renamed.system_key = None
    renamed.is_default = False
    db.commit()

    repaired = ensure_welcome_funnel(db, company_id=company.id)

    assert repaired.id == welcome_funnel.id
    assert repaired.name == "Funnel VIP"
    assert repaired.system_key == "welcome"
    assert repaired.is_default is True
    assert len(
        list(
            db.scalars(
                select(SalesFunnel).where(
                    SalesFunnel.company_id == company.id,
                    SalesFunnel.is_default.is_(True),
                )
            )
        )
    ) == 1


def test_legacy_step_code_collision_does_not_repair_custom_funnel_as_welcome(db):
    company, _ = bootstrap_company(db, "Acme")
    welcome_funnel = get_default_funnel(db, company_id=company.id)

    update_funnel(
        db,
        company_id=company.id,
        funnel_id=welcome_funnel.id,
        payload=FunnelUpdate(
            name="Funnel VIP",
            welcome_message="Hola, cuentame tu caso.",
            capture_fields=["Nombre", "Empresa"],
            assignment_criteria="Atencion VIP",
        ),
    )
    welcome_funnel.system_key = None
    welcome_funnel.is_default = False
    db.commit()

    repaired = ensure_welcome_funnel(db, company_id=company.id)
    funnels = list(
        db.scalars(
            select(SalesFunnel).where(SalesFunnel.company_id == company.id).order_by(SalesFunnel.created_at.asc())
        )
    )

    assert repaired.system_key == "welcome"
    assert repaired.id != welcome_funnel.id
    assert welcome_funnel.system_key is None
    assert welcome_funnel.name == "Funnel VIP"
    assert repaired.welcome_message
    assert repaired.capture_fields == ["Nombre", "Correo", "Ciudad"]
    assert repaired.assignment_criteria
    assert len([funnel for funnel in funnels if funnel.system_key == "welcome"]) == 1


def test_legacy_duplicate_welcome_candidates_do_not_create_a_third_funnel(db):
    company, _ = bootstrap_company(db, "Acme")
    welcome_funnel = get_default_funnel(db, company_id=company.id)
    duplicate = create_funnel(
        db,
        company_id=company.id,
        payload=FunnelCreate(
            name="Funnel de bienvenida legado",
            description="Punto de entrada comercial para conversaciones nuevas.",
            status="active",
            is_default=False,
            welcome_message="Hola, gracias por escribir. Soy el asistente de Swaflow. Para ayudarte mejor, cuentame tu nombre, correo y ciudad.",
            capture_fields=["Nombre", "Correo", "Ciudad"],
            assignment_criteria="Conversaciones nuevas o sin clasificacion comercial previa",
            steps=[
                FunnelStepWrite(
                    position=1,
                    name="Bienvenida",
                    code="bienvenida",
                    prompt=(
                        "Saluda al cliente, agradece su contacto y presenta las opciones "
                        "comerciales principales del tenant."
                    ),
                    objectives=["Saludar", "Detectar interes principal"],
                    transition_criteria="El cliente responde con una necesidad o interes concreto.",
                    status="active",
                    config={"entry_point": True, "capture_fields": ["Nombre", "Correo", "Ciudad"]},
                ),
                FunnelStepWrite(
                    position=2,
                    name="Captura inicial",
                    code="captura_inicial",
                    prompt=(
                        "Solicita solamente los datos que faltan: nombre, correo y ciudad. "
                        "No repitas el telefono si ya viene desde WhatsApp."
                    ),
                    objectives=["Capturar datos iniciales", "Evitar pedir el telefono"],
                    transition_criteria="Los datos iniciales estan completos o el cliente pide avanzar.",
                    status="active",
                    config={"required_fields": ["Nombre", "Correo", "Ciudad"]},
                ),
                FunnelStepWrite(
                    position=3,
                    name="Clasificacion comercial",
                    code="clasificacion_comercial",
                    prompt=(
                        "Clasifica la intencion del cliente y decide el siguiente paso: "
                        "comprar, consultar, agendar o pasar a humano."
                    ),
                    objectives=["Clasificar la intencion", "Elegir el siguiente flujo"],
                    transition_criteria="La intencion comercial queda identificada.",
                    status="active",
                    config={"allowed_outcomes": ["comprar", "consultar", "agendar", "humano"]},
                ),
            ],
        ),
    )

    welcome_funnel.system_key = None
    welcome_funnel.is_default = False
    duplicate.system_key = None
    duplicate.is_default = False
    db.commit()

    repaired = ensure_welcome_funnel(db, company_id=company.id)
    funnels = list(
        db.scalars(
            select(SalesFunnel)
            .where(SalesFunnel.company_id == company.id)
            .order_by(SalesFunnel.created_at.asc())
        )
    )

    assert repaired.id in {welcome_funnel.id, duplicate.id}
    assert len(funnels) == 2
    assert len([funnel for funnel in funnels if funnel.system_key == "welcome"]) == 1
    assert sum(1 for funnel in funnels if funnel.is_default) == 1


def test_get_funnel_returns_404_for_other_tenant(db):
    company, _ = bootstrap_company(db, "Acme")
    other_company, _ = bootstrap_company(db, "Other")
    funnel = get_default_funnel(db, company_id=company.id)

    with pytest.raises(HTTPException) as exc_info:
        get_funnel(db, company_id=other_company.id, funnel_id=funnel.id)

    assert exc_info.value.status_code == 404


def test_order_flow_writes_audit_logs(db):
    company, _ = bootstrap_company(db, "Acme")
    product = Product(
        company_id=company.id,
        name="Producto 1",
        sku="SKU-1",
        price=Decimal("100.00"),
        currency="COP",
        status="active",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="product-1",
    )
    contact = Contact(
        company_id=company.id,
        name="Cliente Uno",
        phone="+573001112233",
    )
    db.add_all([product, contact])
    db.commit()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.commit()
    inventory = Inventory(
        company_id=company.id,
        product_id=product.id,
        quantity_available=10,
        quantity_reserved=0,
    )
    db.add(inventory)
    db.commit()
    bootstrap_payment_integration(db, company_id=company.id)

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)
    mark_paid_by_reference(db, payment_reference=order.payment_reference or "", provider="mock")

    actions = [log.action for log in list_audit_logs(db, company_id=company.id, limit=50, offset=0)]
    assert "order.created" in actions
    assert "order.payment_link_generated" in actions
    assert "order.paid" in actions


def test_login_works_without_company_id_and_user_can_change_password(db):
    _, owner = bootstrap_company(db, "Acme")

    assert authenticate_user(db, email=owner.email, password="super-secret") == owner

    change_own_password(
        db,
        user=owner,
        payload=PasswordChangeRequest(
            current_password="super-secret",
            new_password="new-super-secret",
        ),
    )

    assert authenticate_user(db, email=owner.email, password="super-secret") is None
    assert authenticate_user(db, email=owner.email, password="new-super-secret") == owner


def test_change_own_password_survives_audit_failure(db, monkeypatch):
    _, owner = bootstrap_company(db, "Acme")

    def boom(*args, **kwargs):
        raise RuntimeError("audit failed")

    monkeypatch.setattr("app.auth.service.record_audit_best_effort", boom)

    change_own_password(
        db,
        user=owner,
        payload=PasswordChangeRequest(
            current_password="super-secret",
            new_password="new-super-secret",
        ),
    )

    assert authenticate_user(db, email=owner.email, password="super-secret") is None
    assert authenticate_user(db, email=owner.email, password="new-super-secret") == owner


def test_current_user_payload_includes_company_branding(db):
    company, owner = bootstrap_company(db, "Acme")
    company.logo_url = "https://cdn.example.com/acme/logo.svg"
    company.banner_url = "https://cdn.example.com/acme/banner.png"
    company.profile_url = "https://cdn.example.com/acme/profile.jpg"
    db.commit()

    payload = build_current_user_payload(owner)

    assert payload["company_logo_url"] == "https://cdn.example.com/acme/logo.svg"
    assert payload["company_banner_url"] == "https://cdn.example.com/acme/banner.png"
    assert payload["company_profile_url"] == "https://cdn.example.com/acme/profile.jpg"


def test_company_profile_update_persists_configuration_fields(db):
    company, _ = bootstrap_company(db, "Acme")

    updated = update_company(
        db,
        company_id=company.id,
        current_company_id=company.id,
        payload=CompanyUpdate(
            name="Acme Comercial",
            contact_email="contacto@acme.com",
            contact_phone="+57 300 111 2233",
            currency="COP",
            timezone="America/Bogota",
            business_mode="mixed",
            logo_url="https://cdn.example.com/acme/logo.svg",
            banner_url="https://cdn.example.com/acme/banner.png",
            profile_url="https://cdn.example.com/acme/profile.jpg",
        ),
    )

    assert updated.name == "Acme Comercial"
    assert updated.contact_email == "contacto@acme.com"
    assert updated.contact_phone == "+57 300 111 2233"
    assert updated.currency == "COP"
    assert updated.timezone == "America/Bogota"
    assert updated.business_mode == "mixed"
    assert updated.logo_url == "https://cdn.example.com/acme/logo.svg"
    assert updated.banner_url == "https://cdn.example.com/acme/banner.png"
    assert updated.profile_url == "https://cdn.example.com/acme/profile.jpg"

    reloaded = db.scalar(select(Company).where(Company.id == company.id))
    assert reloaded is not None
    assert reloaded.name == "Acme Comercial"
    assert reloaded.business_mode == "mixed"
    assert reloaded.logo_url == "https://cdn.example.com/acme/logo.svg"
    assert reloaded.banner_url == "https://cdn.example.com/acme/banner.png"
    assert reloaded.profile_url == "https://cdn.example.com/acme/profile.jpg"


def test_company_profile_update_rejects_invalid_timezone(db):
    company, _ = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc:
        update_company(
            db,
            company_id=company.id,
            current_company_id=company.id,
            payload=CompanyUpdate(timezone="Mars/Phobos"),
        )

    assert exc.value.status_code == 422


def test_company_profile_update_toggles_auto_assign_for_single_additional_user_chats(db):
    company, owner = bootstrap_company(db, "Acme")

    updated = update_company(
        db,
        company_id=company.id,
        current_company_id=company.id,
        payload=CompanyUpdate(
            auto_assign_single_additional_user_chats=False,
        ),
        actor_user=owner,
    )

    assert updated.auto_assign_single_additional_user_chats is False

    reloaded = db.scalar(select(Company).where(Company.id == company.id))
    assert reloaded is not None
    assert reloaded.auto_assign_single_additional_user_chats is False


def test_create_conversation_auto_assigns_single_active_additional_user_when_enabled(db):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente 1",
            email="agent1@acme.example.com",
            password="super-secret-9",
            role="agent",
        ),
    )
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )

    assert conversation.assigned_user_id == agent.id
    assert conversation.status == "waiting_human"


def test_create_conversation_keeps_chat_available_when_auto_assign_is_disabled(db):
    company, owner = bootstrap_company(db, "Acme")
    create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente 1",
            email="agent2@acme.example.com",
            password="super-secret-10",
            role="agent",
        ),
    )
    update_company(
        db,
        company_id=company.id,
        current_company_id=company.id,
        payload=CompanyUpdate(auto_assign_single_additional_user_chats=False),
        actor_user=owner,
    )
    contact = Contact(company_id=company.id, name="Cliente 2", phone="+573001112234")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )

    assert conversation.assigned_user_id is None
    assert conversation.status == "open"


def test_company_profile_update_preserves_legacy_business_mode_values(db):
    company, _ = bootstrap_company(db, "Acme")
    company.business_mode = "legacy"
    db.commit()

    updated = update_company(
        db,
        company_id=company.id,
        current_company_id=company.id,
        payload=CompanyUpdate(
            name="Acme Comercial",
            business_mode="legacy",
        ),
    )

    assert updated.name == "Acme Comercial"
    assert updated.business_mode == "legacy"


def test_company_profile_update_rejects_unknown_business_mode_values(db):
    company, _ = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc:
        update_company(
            db,
            company_id=company.id,
            current_company_id=company.id,
            payload=CompanyUpdate(
                name="Acme Comercial",
                business_mode="inventado",
            ),
        )

    assert exc.value.status_code == 422


def test_company_profile_cross_tenant_access_returns_404(db):
    company_a, _ = bootstrap_company(db, "Acme")
    company_b, _ = bootstrap_company(db, "Beta")

    with pytest.raises(HTTPException) as exc:
        update_company(
            db,
            company_id=company_a.id,
            current_company_id=company_b.id,
            payload=CompanyUpdate(
                name="Acme Comercial",
            ),
        )
    assert exc.value.status_code == 404


def test_company_profile_read_is_tenant_scoped(db):
    company, _ = bootstrap_company(db, "Acme")
    company.logo_url = "https://cdn.example.com/acme/logo.svg"
    company.banner_url = "https://cdn.example.com/acme/banner.png"
    company.profile_url = "https://cdn.example.com/acme/profile.jpg"
    db.commit()

    loaded = service.get_company_for_user(
        db,
        company_id=company.id,
        current_company_id=company.id,
    )

    assert loaded.logo_url == "https://cdn.example.com/acme/logo.svg"
    assert loaded.banner_url == "https://cdn.example.com/acme/banner.png"
    assert loaded.profile_url == "https://cdn.example.com/acme/profile.jpg"

    other_company, _ = bootstrap_company(db, "Beta")
    with pytest.raises(HTTPException) as exc:
        service.get_company_for_user(
            db,
            company_id=company.id,
            current_company_id=other_company.id,
        )
    assert exc.value.status_code == 404


def test_company_profile_same_tenant_agent_access_returns_404(db):
    company, _ = bootstrap_company(db, "Acme")
    agent = User(
        company_id=company.id,
        name="Agente Acme",
        email="agent@acme.example.com",
        password_hash="not-used",
        role="agent",
    )
    db.add(agent)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        service.require_company_profile_access(agent)
    assert exc.value.status_code == 403


def test_superadmin_access_can_cross_tenant_scope(db):
    _, owner = bootstrap_company(db, "Acme")
    swateck, _ = bootstrap_company(db, "Swateck")
    superadmin = User(
        company_id=swateck.id,
        name="Superusuario Swateck",
        email="admin@swateck.com",
        password_hash="not-used",
        role="superadmin",
    )
    db.add(superadmin)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        get_user(db, company_id=swateck.id, user_id=owner.id)
    assert exc.value.status_code == 404

    assert get_user(db, company_id=None, user_id=owner.id).id == owner.id


def test_product_lookup_is_tenant_scoped(db):
    company_a, _ = bootstrap_company(db, "Acme")
    company_b, _ = bootstrap_company(db, "Beta")
    product = Product(
        company_id=company_a.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
    )
    db.add(product)
    db.commit()

    assert get_product(db, company_id=company_a.id, product_id=product.id).id == product.id
    with pytest.raises(HTTPException) as exc:
        get_product(db, company_id=company_b.id, product_id=product.id)
    assert exc.value.status_code == 404


def test_order_flow_reserves_stock_and_settles_payment(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=5)
    db.add(inventory)
    db.commit()
    bootstrap_payment_integration(db, company_id=company.id)

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=2)],
        ),
    )

    assert order.total == Decimal("160000.00")
    assert order.status == "pending"
    assert inventory.quantity_reserved == 2

    order = generate_payment_link(db, company_id=company.id, order_id=order.id)
    assert order.status == "waiting_payment"
    assert order.payment_reference
    assert order.payment_link

    paid_order = mark_paid_by_reference(db, payment_reference=order.payment_reference)
    assert paid_order.status == "paid"
    assert inventory.quantity_available == 3
    assert inventory.quantity_reserved == 0


def test_generate_payment_link_requires_active_payment_integration(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    db.add(Inventory(company_id=company.id, product_id=product.id, quantity_available=5))
    db.commit()

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        generate_payment_link(db, company_id=company.id, order_id=order.id)

    assert exc_info.value.status_code == 422
    assert "Active payment integration is required" in str(exc_info.value.detail)


def test_order_creation_is_idempotent_and_does_not_duplicate_stock_reservation(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=5)
    db.add(inventory)
    db.commit()

    payload = OrderCreate(
        contact_id=contact.id,
        conversation_id=conversation.id,
        items=[OrderItemCreate(product_id=product.id, quantity=2)],
        metadata={"idempotency_key": "inbox-order-123"},
    )

    first_order = create_order(db, company_id=company.id, payload=payload)
    second_order = create_order(db, company_id=company.id, payload=payload)

    assert second_order.id == first_order.id
    assert inventory.quantity_reserved == 2
    assert len(first_order.items) == 1
    assert first_order.conversation_id == conversation.id
    assert first_order.idempotency_key == "inbox-order-123"


def test_order_creation_without_explicit_idempotency_key_allows_legitimate_repeats(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=5)
    db.add(inventory)
    db.commit()

    payload = OrderCreate(
        contact_id=contact.id,
        conversation_id=conversation.id,
        items=[OrderItemCreate(product_id=product.id, quantity=1)],
        metadata={},
    )

    first_order = create_order(db, company_id=company.id, payload=payload)
    second_order = create_order(db, company_id=company.id, payload=payload)

    assert first_order.id != second_order.id
    assert inventory.quantity_reserved == 2
    assert first_order.idempotency_key != second_order.idempotency_key


def test_order_creation_rejects_closed_conversation(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="closed")
    db.add(conversation)
    db.flush()
    db.add(Inventory(company_id=company.id, product_id=product.id, quantity_available=5))
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db,
            company_id=company.id,
            payload=OrderCreate(
                contact_id=contact.id,
                conversation_id=conversation.id,
                items=[OrderItemCreate(product_id=product.id, quantity=1)],
            ),
        )

    assert exc_info.value.status_code == 422
    assert "Conversation must be active" in str(exc_info.value.detail)


def test_order_creation_returns_404_for_cross_tenant_conversation(db):
    company, _ = bootstrap_company(db, "Acme")
    other_company, _ = bootstrap_company(db, "Bravo")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    other_contact = Contact(company_id=other_company.id, name="Otro cliente", phone="573000000001")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, other_contact, product])
    db.flush()
    other_conversation = Conversation(
        company_id=other_company.id,
        contact_id=other_contact.id,
        status="open",
    )
    db.add(other_conversation)
    db.add(Inventory(company_id=company.id, product_id=product.id, quantity_available=5))
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db,
            company_id=company.id,
            payload=OrderCreate(
                contact_id=contact.id,
                conversation_id=other_conversation.id,
                items=[OrderItemCreate(product_id=product.id, quantity=1)],
            ),
        )

    assert exc_info.value.status_code == 404


def test_list_orders_sorts_and_filters_by_relationships_and_dates(db):
    company, _ = bootstrap_company(db, "Acme")
    owner = db.scalar(select(User).where(User.company_id == company.id, User.role == "owner"))
    agent_one = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente Uno",
            email="agent-one@acme.example.com",
            password="super-secret-11",
            role="agent",
        ),
    )
    agent_two = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente Dos",
            email="agent-two@acme.example.com",
            password="super-secret-12",
            role="agent",
        ),
    )
    bootstrap_payment_integration(db, company_id=company.id)

    def create_filterable_order(
        *,
        contact_name: str,
        contact_phone: str,
        product_name: str,
        sku: str,
        created_at: datetime,
        status_mode: str,
        assigned_user: User | None = None,
    ) -> tuple[Order, Contact, Product, Conversation]:
        contact = Contact(company_id=company.id, name=contact_name, phone=contact_phone)
        product = Product(
            company_id=company.id,
            name=product_name,
            sku=sku,
            price=Decimal("50000.00"),
            currency="COP",
            whatsapp_catalog_id=f"catalog-{sku.lower()}",
            whatsapp_product_retailer_id=f"retailer-{sku.lower()}",
        )
        db.add_all([contact, product])
        db.flush()
        conversation = Conversation(
            company_id=company.id,
            contact_id=contact.id,
            status="waiting_human" if assigned_user else "open",
            assigned_user_id=assigned_user.id if assigned_user else None,
        )
        db.add(conversation)
        db.add(
            Inventory(
                company_id=company.id,
                product_id=product.id,
                quantity_available=10,
                quantity_reserved=0,
            )
        )
        db.commit()

        order = create_order(
            db,
            company_id=company.id,
            payload=OrderCreate(
                contact_id=contact.id,
                conversation_id=conversation.id,
                items=[OrderItemCreate(product_id=product.id, quantity=1)],
            ),
        )
        if status_mode == "waiting_payment":
            order = generate_payment_link(db, company_id=company.id, order_id=order.id)
        elif status_mode == "paid":
            order = generate_payment_link(db, company_id=company.id, order_id=order.id)
            order = mark_paid_by_reference(
                db,
                payment_reference=order.payment_reference or "",
                provider=order.payment_provider or "mock",
            )
        elif status_mode == "cancelled":
            order = cancel_order(db, company_id=company.id, order_id=order.id)

        order.created_at = created_at
        db.commit()
        return order, contact, product, conversation

    pending_order, pending_contact, pending_product, pending_conversation = create_filterable_order(
        contact_name="Cliente Pendiente",
        contact_phone="573000000100",
        product_name="Producto Pendiente",
        sku="PEND-1",
        created_at=datetime(2026, 5, 10, 9, 0, tzinfo=UTC),
        status_mode="pending",
    )
    waiting_order, waiting_contact, waiting_product, waiting_conversation = create_filterable_order(
        contact_name="Cliente Pago",
        contact_phone="573000000200",
        product_name="Producto Pago",
        sku="PAGO-1",
        created_at=datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
        status_mode="waiting_payment",
        assigned_user=agent_one,
    )
    paid_order, paid_contact, paid_product, paid_conversation = create_filterable_order(
        contact_name="Cliente Pagado",
        contact_phone="573000000300",
        product_name="Producto Pagado",
        sku="PAGO-2",
        created_at=datetime(2026, 7, 20, 9, 0, tzinfo=UTC),
        status_mode="paid",
        assigned_user=agent_two,
    )

    ordered = list_orders(db, company_id=company.id, limit=50, offset=0)
    assert [order.id for order in ordered] == [paid_order.id, waiting_order.id, pending_order.id]

    july_orders = list_orders(
        db,
        company_id=company.id,
        limit=50,
        offset=0,
        created_from=date(2026, 7, 1),
        created_to=date(2026, 7, 31),
    )
    assert [order.id for order in july_orders] == [paid_order.id]

    waiting_status_orders = list_orders(
        db,
        company_id=company.id,
        limit=50,
        offset=0,
        status_filter="waiting_payment",
    )
    assert [order.id for order in waiting_status_orders] == [waiting_order.id]

    contact_orders = list_orders(
        db,
        company_id=company.id,
        limit=50,
        offset=0,
        contact_id=waiting_contact.id,
    )
    assert [order.id for order in contact_orders] == [waiting_order.id]

    product_orders = list_orders(
        db,
        company_id=company.id,
        limit=50,
        offset=0,
        product_id=waiting_product.id,
    )
    assert [order.id for order in product_orders] == [waiting_order.id]

    conversation_orders = list_orders(
        db,
        company_id=company.id,
        limit=50,
        offset=0,
        conversation_id=waiting_conversation.id,
    )
    assert [order.id for order in conversation_orders] == [waiting_order.id]

    assigned_user_orders = list_orders(
        db,
        company_id=company.id,
        limit=50,
        offset=0,
        assigned_user_id=agent_one.id,
    )
    assert [order.id for order in assigned_user_orders] == [waiting_order.id]

    paid_status_orders = list_orders(
        db,
        company_id=company.id,
        limit=50,
        offset=0,
        status_filter="paid",
    )
    assert [order.id for order in paid_status_orders] == [paid_order.id]

    assert pending_contact.id == pending_order.contact_id
    assert pending_product.id == pending_order.items[0].product_id
    assert paid_contact.id == paid_order.contact_id
    assert paid_product.id == paid_order.items[0].product_id
    assert owner is not None


def test_list_orders_keeps_tenant_isolation_when_other_company_has_matching_orders(db):
    company, _ = bootstrap_company(db, "Acme")
    other_company, _ = bootstrap_company(db, "Beta")
    bootstrap_payment_integration(db, company_id=company.id)
    bootstrap_payment_integration(db, company_id=other_company.id)

    contact = Contact(company_id=company.id, name="Cliente Acme", phone="573000000400")
    other_contact = Contact(company_id=other_company.id, name="Cliente Beta", phone="573000000500")
    product = Product(
        company_id=company.id,
        name="Producto Acme",
        sku="ACME-1",
        price=Decimal("70000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-acme",
        whatsapp_product_retailer_id="retailer-acme",
    )
    other_product = Product(
        company_id=other_company.id,
        name="Producto Beta",
        sku="BETA-1",
        price=Decimal("70000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-beta",
        whatsapp_product_retailer_id="retailer-beta",
    )
    db.add_all([contact, other_contact, product, other_product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    other_conversation = Conversation(
        company_id=other_company.id,
        contact_id=other_contact.id,
        status="open",
    )
    db.add_all([conversation, other_conversation])
    db.add_all(
        [
            Inventory(company_id=company.id, product_id=product.id, quantity_available=10),
            Inventory(company_id=other_company.id, product_id=other_product.id, quantity_available=10),
        ]
    )
    db.commit()

    company_order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    other_order = create_order(
        db,
        company_id=other_company.id,
        payload=OrderCreate(
            contact_id=other_contact.id,
            conversation_id=other_conversation.id,
            items=[OrderItemCreate(product_id=other_product.id, quantity=1)],
        ),
    )
    company_order.created_at = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)
    other_order.created_at = datetime(2026, 7, 21, 9, 0, tzinfo=UTC)
    db.commit()

    company_orders = list_orders(db, company_id=company.id, limit=50, offset=0)
    assert [order.id for order in company_orders] == [company_order.id]
    assert other_order.id not in {order.id for order in company_orders}


def test_list_orders_uses_tenant_timezone_for_date_filters(db):
    company, _ = bootstrap_company(db, "Acme")
    company.timezone = "America/Bogota"
    db.commit()
    bootstrap_payment_integration(db, company_id=company.id)

    contact = Contact(company_id=company.id, name="Cliente Acme", phone="573000000600")
    product = Product(
        company_id=company.id,
        name="Producto Acme",
        sku="ACME-TZ",
        price=Decimal("70000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-acme-tz",
        whatsapp_product_retailer_id="retailer-acme-tz",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.add(
        Inventory(
            company_id=company.id,
            product_id=product.id,
            quantity_available=10,
            quantity_reserved=0,
        )
    )
    db.commit()

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order.created_at = datetime(2026, 7, 21, 4, 30, tzinfo=UTC)
    db.commit()

    filtered = list_orders(
        db,
        company_id=company.id,
        limit=50,
        offset=0,
        created_from=date(2026, 7, 20),
        created_to=date(2026, 7, 20),
    )

    assert [item.id for item in filtered] == [order.id]


def test_payment_integration_requires_provider_and_webhook_secret_when_active(db):
    company, _ = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc_info:
        create_integration(
            db,
            company_id=company.id,
            payload=IntegrationCreate(
                type="payments",
                credentials=json.dumps({"private_key": "pk_test"}),
                config={
                    "environment": "sandbox",
                    "currency": "COP",
                    "payment_link_ttl_minutes": "45",
                },
            ),
        )
    assert exc_info.value.status_code == 422
    assert "Payment provider is required" in str(exc_info.value.detail)

    with pytest.raises(HTTPException) as exc_info:
        create_integration(
            db,
            company_id=company.id,
            payload=IntegrationCreate(
                type="payments",
                credentials=json.dumps({"private_key": "pk_test"}),
                config={
                    "provider": "wompi",
                    "environment": "sandbox",
                    "currency": "COP",
                    "payment_link_ttl_minutes": "45",
                },
            ),
        )
    assert exc_info.value.status_code == 422
    assert "Wompi events secret is required" in str(exc_info.value.detail)

    integration = create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="payments",
            credentials=json.dumps(
                {"private_key": "pk_test", "events_secret": "evt_test"}
            ),
            config={
                "provider": "wompi",
                "environment": "sandbox",
                "currency": "COP",
                "payment_link_ttl_minutes": "45",
            },
        ),
    )

    stored = db.scalar(select(CompanyIntegration).where(CompanyIntegration.id == integration.id))
    assert stored is not None
    assert json.loads(decrypt_secret(stored.credentials_encrypted or "{}")) == {
        "private_key": "pk_test",
        "events_secret": "evt_test",
    }

    updated = update_integration(
        db,
        company_id=company.id,
        integration_id=integration.id,
        payload=IntegrationUpdate(
            config={
                "provider": "wompi",
                "environment": "sandbox",
                "currency": "COP",
                "payment_link_ttl_minutes": "90",
            }
        ),
    )
    assert updated.status == "active"
    assert updated.config["payment_link_ttl_minutes"] == "90"
    assert json.loads(decrypt_secret(updated.credentials_encrypted or "{}")) == {
        "private_key": "pk_test",
        "events_secret": "evt_test",
    }


def test_payment_integration_update_rejects_invalid_contracts(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    integration = create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="payments",
            credentials=json.dumps(
                {"private_key": "pk_test", "events_secret": "evt_test"}
            ),
            config={
                "provider": "wompi",
                "environment": "sandbox",
                "currency": "COP",
                "payment_link_ttl_minutes": "45",
            },
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        update_integration(
            db,
            company_id=company.id,
            integration_id=integration.id,
            payload=IntegrationUpdate(
                config={
                    "provider": "stripe",
                    "environment": "sandbox",
                    "currency": "COP",
                    "payment_link_ttl_minutes": "45",
                }
            ),
        )
    assert exc_info.value.status_code == 422
    assert "Unsupported payment provider" in str(exc_info.value.detail)

    monkeypatch.setattr(
        "app.payments.contract.get_settings",
        lambda: SimpleNamespace(app_env="production"),
    )
    with pytest.raises(HTTPException) as exc_info:
        update_integration(
            db,
            company_id=company.id,
            integration_id=integration.id,
            payload=IntegrationUpdate(
                config={
                    "provider": "mock",
                    "environment": "sandbox",
                    "currency": "COP",
                    "payment_link_ttl_minutes": "45",
                }
            ),
        )
    assert exc_info.value.status_code == 422
    assert "Local payment provider is not allowed in production" in str(exc_info.value.detail)


def test_audit_logs_redact_integration_secrets(db):
    company, _ = bootstrap_company(db, "Acme")

    def collect_keys(value):
        keys = set()
        if isinstance(value, dict):
            for key, child in value.items():
                keys.add(key)
                keys.update(collect_keys(child))
        elif isinstance(value, list):
            for item in value:
                keys.update(collect_keys(item))
        elif isinstance(value, tuple):
            for item in value:
                keys.update(collect_keys(item))
        return keys

    integration = create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="payments",
            credentials=json.dumps(
                {"private_key": "pk_test", "events_secret": "evt_test"}
            ),
            config={
                "provider": "wompi",
                "environment": "sandbox",
                "currency": "COP",
            },
        ),
    )

    update_integration(
        db,
        company_id=company.id,
        integration_id=integration.id,
        payload=IntegrationUpdate(
            credentials=json.dumps(
                {"private_key": "pk_test_2", "events_secret": "evt_test_2"}
            )
        ),
    )

    integration_log = next(
        log for log in list_audit_logs(db, company_id=company.id, limit=10, offset=0)
        if log.action == "integration.updated"
    )
    assert "credentials" not in integration_log.metadata_json
    assert "secret_token" not in integration_log.metadata_json

    webhook = create_outbound_webhook(
        db,
        company_id=company.id,
        payload=OutboundWebhookCreate(
            event_type="order.paid",
            target_url="https://example.com/webhooks/orders",
            secret_token="initial-secret",
            active=True,
        ),
    )

    update_outbound_webhook(
        db,
        company_id=company.id,
        webhook_id=webhook.id,
        payload=OutboundWebhookUpdate(secret_token="rotated-secret"),
    )

    webhook_log = next(
        log for log in list_audit_logs(db, company_id=company.id, limit=10, offset=0)
        if log.action == "outbound_webhook.updated"
    )
    assert "credentials" not in webhook_log.metadata_json
    assert "secret_token" not in webhook_log.metadata_json

    update_integration(
        db,
        company_id=company.id,
        integration_id=integration.id,
        payload=IntegrationUpdate(
            config={
                "provider": "wompi",
                "environment": "sandbox",
                "currency": "COP",
                "payment_link_ttl_minutes": "90",
                "nested": {
                    "token_count": 3,
                    "signature_algorithm": "RS256",
                    "secret_token": "nested-secret",
                    "api_key": "nested-api-key",
                    "access_token_id": "nested-access-token-id",
                    "secretTokenMarker": "nested-secret-token-marker",
                    "clientSecretJson": "nested-client-secret-json",
                    "items": [
                        {"client_secret": "nested-client-secret"},
                        {"signature": "nested-signature"},
                    ],
                },
            }
        ),
    )

    nested_integration_log = next(
        log
        for log in list_audit_logs(db, company_id=company.id, limit=20, offset=0)
        if log.action == "integration.updated"
        and isinstance(log.metadata_json, dict)
        and isinstance(log.metadata_json.get("config"), dict)
        and "nested" in log.metadata_json["config"]
    )
    nested_serialized = json.dumps(
        nested_integration_log.metadata_json, ensure_ascii=False, sort_keys=True
    )
    assert "nested-secret" not in nested_serialized
    assert "nested-api-key" not in nested_serialized
    assert "nested-client-secret" not in nested_serialized
    assert "nested-signature" not in nested_serialized
    assert "nested-access-token-id" not in nested_serialized
    assert "nested-secret-token-marker" not in nested_serialized
    assert "nested-client-secret-json" not in nested_serialized
    assert "secret_token" not in nested_serialized
    assert "api_key" not in nested_serialized
    assert "client_secret" not in nested_serialized
    assert not {"credentials", "secret_token", "api_key", "client_secret", "signature"} & collect_keys(
        nested_integration_log.metadata_json
    )
    assert nested_integration_log.metadata_json["config"]["nested"]["token_count"] == 3
    assert (
        nested_integration_log.metadata_json["config"]["nested"]["signature_algorithm"]
        == "RS256"
    )


def test_email_notification_uses_tenant_brand_and_recipient_headers(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(
        company_id=company.id,
        name="Cliente Demo",
        email="cliente@acme.com",
        phone="573000000000",
    )
    db.add(contact)
    db.flush()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="email",
            credentials=json.dumps({"password": "smtp-secret"}),
            config={
                "provider": "smtp",
                "from_email": "notificaciones@acme.com",
                "smtp_host": "smtp.acme.com",
                "smtp_port": "587",
            },
        ),
    )

    order = Order(
        company_id=company.id,
        contact_id=contact.id,
        status="paid",
        payment_status="paid",
        total=Decimal("125000.00"),
        currency="COP",
        payment_reference="ref-123",
    )
    db.add(order)
    db.commit()

    captured: dict[str, object] = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            captured["starttls"] = True

        def login(self, username, password):
            captured["login"] = (username, password)

        def send_message(self, message):
            captured["message"] = message

    monkeypatch.setattr("app.payments.notifications.smtplib.SMTP", FakeSMTP)

    notify_order_paid(db, order=order)

    message = captured["message"]
    assert captured["host"] == "smtp.acme.com"
    assert captured["port"] == 587
    assert captured["starttls"] is True
    assert captured["login"] == ("notificaciones@acme.com", "smtp-secret")
    assert message["From"] == "Acme <notificaciones@acme.com>"
    assert message["Subject"] == f"Pago confirmado - Acme - Orden {str(order.id)[:8]}"
    assert "Pago confirmado en Acme." in message.get_content()
    assert "Empresa: Acme" in message.get_content()
    assert "Correo cliente: cliente@acme.com" in message.get_content()


def test_email_notification_delivery_failure_is_audited_without_breaking_flow(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(
        company_id=company.id,
        name="Cliente Demo",
        email="cliente@acme.com",
        phone="573000000000",
    )
    db.add(contact)
    db.flush()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="email",
            credentials=json.dumps({"password": "smtp-secret"}),
            config={
                "provider": "smtp",
                "from_email": "notificaciones@acme.com",
                "smtp_host": "smtp.acme.com",
                "smtp_port": "587",
            },
        ),
    )

    order = Order(
        company_id=company.id,
        contact_id=contact.id,
        status="paid",
        payment_status="paid",
        total=Decimal("125000.00"),
        currency="COP",
        payment_reference="ref-456",
    )
    db.add(order)
    db.commit()

    class FailingSMTP:
        def __init__(self, host, port, timeout):
            self.host = host

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            return None

        def send_message(self, message):
            raise RuntimeError("smtp down")

    monkeypatch.setattr("app.payments.notifications.smtplib.SMTP", FailingSMTP)

    notify_order_paid(db, order=order)

    audit_log = next(
        log
        for log in list_audit_logs(db, company_id=company.id, limit=20, offset=0)
        if log.action == "email_notification.delivery_failed"
    )
    assert audit_log.entity_id is not None
    assert audit_log.metadata_json["channel"] == "email"
    assert audit_log.metadata_json["company_name"] == "Acme"
    assert audit_log.metadata_json["order_id"] == str(order.id)
    assert audit_log.metadata_json["order_reference"] == "ref-456"
    assert audit_log.metadata_json["recipient_count"] == 2
    assert audit_log.metadata_json["error_type"] == "RuntimeError"
    assert "smtp-secret" not in audit_log.metadata_json


def test_email_notification_missing_smtp_config_is_audited_without_breaking_flow(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(
        company_id=company.id,
        name="Cliente Demo",
        email="cliente@acme.com",
        phone="573000000000",
    )
    db.add(contact)
    db.flush()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="email",
            credentials=json.dumps({"password": "smtp-secret"}),
            config={
                "provider": "smtp",
                "from_email": "notificaciones@acme.com",
            },
        ),
    )

    order = Order(
        company_id=company.id,
        contact_id=contact.id,
        status="paid",
        payment_status="paid",
        total=Decimal("125000.00"),
        currency="COP",
        payment_reference="ref-789",
    )
    db.add(order)
    db.commit()

    called = {"smtp": False}

    class UnexpectedSMTP:
        def __init__(self, host, port, timeout):
            called["smtp"] = True

    monkeypatch.setattr("app.payments.notifications.smtplib.SMTP", UnexpectedSMTP)

    notify_order_paid(db, order=order)

    audit_log = next(
        log
        for log in list_audit_logs(db, company_id=company.id, limit=20, offset=0)
        if log.action == "email_notification.delivery_failed"
    )
    assert audit_log.metadata_json["channel"] == "email"
    assert audit_log.metadata_json["order_id"] == str(order.id)
    assert audit_log.metadata_json["error_type"] == "ValueError"
    assert called["smtp"] is False


def test_outbound_webhook_dispatch_signs_secret_and_records_delivery_failure(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    secret = "webhook-secret"

    failing_webhook = create_outbound_webhook(
        db,
        company_id=company.id,
        payload=OutboundWebhookCreate(
            event_type="order.paid",
            target_url="https://example.com/webhooks/fail",
            active=True,
        ),
    )
    signed_webhook = create_outbound_webhook(
        db,
        company_id=company.id,
        payload=OutboundWebhookCreate(
            event_type="order.paid",
            target_url="https://example.com/webhooks/signed",
            secret_token=secret,
            active=True,
        ),
    )
    create_outbound_webhook(
        db,
        company_id=company.id,
        payload=OutboundWebhookCreate(
            event_type="order.paid",
            target_url="https://example.com/webhooks/inactive",
            active=False,
        ),
    )

    calls: list[dict[str, object]] = []

    class FakeResponse:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "boom",
                    request=httpx.Request("POST", "https://example.com/webhooks/fail"),
                    response=httpx.Response(self.status_code),
                )

    class FakeClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, target_url, content=None, headers=None):
            calls.append(
                {
                    "target_url": target_url,
                    "content": content,
                    "headers": headers,
                }
            )
            if target_url.endswith("/fail"):
                return FakeResponse(503)
            return FakeResponse(204)

    monkeypatch.setattr("app.events.dispatcher.httpx.Client", FakeClient)

    event = Event(
        company_id=company.id,
        event_type="order.paid",
        payload={"order_id": "order-123", "total": "125000.00"},
        status="pending",
    )
    db.add(event)
    db.flush()

    from app.events.dispatcher import dispatch_event

    dispatch_event(db, event)
    db.commit()
    db.refresh(event)

    assert event.status == "delivery_failed"
    assert len(calls) == 2
    assert all(call["target_url"] != "https://example.com/webhooks/inactive" for call in calls)

    signed_call = next(call for call in calls if call["target_url"] == "https://example.com/webhooks/signed")
    expected_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        signed_call["content"],
        hashlib.sha256,
    ).hexdigest()
    assert signed_call["headers"]["X-SwaFlow-Signature"] == expected_signature
    assert signed_call["headers"]["X-SwaFlow-Event"] == "order.paid"
    assert signed_call["headers"]["X-SwaFlow-Event-Id"] == str(event.id)

    failure_log = next(
        log
        for log in list_audit_logs(db, company_id=company.id, limit=20, offset=0)
        if log.action == "outbound_webhook.delivery_failed"
    )
    assert failure_log.entity_id == failing_webhook.id
    assert failure_log.metadata_json["event_id"] == str(event.id)
    assert failure_log.metadata_json["event_type"] == "order.paid"
    assert failure_log.metadata_json["target_url"] == "https://example.com/webhooks/fail"
    assert failure_log.metadata_json["response_status_code"] == 503


def test_outbound_webhook_dispatch_survives_audit_failure(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")

    create_outbound_webhook(
        db,
        company_id=company.id,
        payload=OutboundWebhookCreate(
            event_type="order.paid",
            target_url="https://example.com/webhooks/fail",
            active=True,
        ),
    )

    class FakeResponse:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("POST", "https://example.com/webhooks/fail"),
                response=httpx.Response(self.status_code),
            )

    class FakeClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, target_url, content=None, headers=None):
            return FakeResponse(503)

    def boom(*args, **kwargs):
        raise RuntimeError("audit down")

    monkeypatch.setattr("app.events.dispatcher.httpx.Client", FakeClient)
    monkeypatch.setattr("app.events.dispatcher.record_audit", boom)

    event = Event(
        company_id=company.id,
        event_type="order.paid",
        payload={"order_id": "order-456"},
        status="pending",
    )
    db.add(event)
    db.flush()

    from app.events.dispatcher import dispatch_event

    dispatch_event(db, event)
    db.commit()
    db.refresh(event)

    assert event.status == "delivery_failed"
    assert event.processed_at is not None


def test_calendar_integration_validates_provider_and_normalizes_alias(db):
    company, _ = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc_info:
        create_integration(
            db,
            company_id=company.id,
            payload=IntegrationCreate(
                type="calendar",
                credentials="calendar-secret",
                config={
                    "provider": "calendly",
                    "calendar_id": "primary",
                    "timezone": "America/Bogota",
                },
            ),
        )
    assert exc_info.value.status_code == 422
    assert "Google Calendar or Microsoft Calendar" in str(exc_info.value.detail)

    integration = create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="calendar",
            credentials="calendar-secret",
            config={
                "calendar_id": "primary",
                "timezone": "America/Bogota",
            },
        ),
    )
    assert integration.config["provider"] == "google_calendar"

    with pytest.raises(HTTPException) as exc_info:
        create_integration(
            db,
            company_id=company.id,
            payload=IntegrationCreate(
                type="calendar",
                credentials="",
                config={
                    "provider": "google_calendar",
                    "calendar_id": "primary",
                    "timezone": "America/Bogota",
                },
            ),
        )
    assert exc_info.value.status_code == 422
    assert "Calendar credentials are required" in str(exc_info.value.detail)

    integration = create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="calendar",
            credentials="calendar-secret",
            config={
                "provider": "outlook_calendar",
                "calendar_id": "primary",
                "timezone": "America/Bogota",
            },
        ),
    )

    assert integration.config["provider"] == "microsoft_calendar"
    assert integration.config["api_base_url"] == "https://graph.microsoft.com/v1.0"
    assert integration.config["create_event_path"] == "me/calendars/{calendar_id}/events"
    assert integration.config["update_event_path"] == "me/events/{event_id}"
    assert integration.config["response_event_id_path"] == "id"
    stored = db.scalar(select(CompanyIntegration).where(CompanyIntegration.id == integration.id))
    assert stored is not None
    assert decrypt_secret(stored.credentials_encrypted or "") == "calendar-secret"


def test_calendar_integration_update_rejects_invalid_contracts(db):
    company, _ = bootstrap_company(db, "Acme")
    integration = create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="calendar",
            credentials="calendar-secret",
            config={
                "provider": "google_calendar",
                "calendar_id": "primary",
                "timezone": "America/Bogota",
            },
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        update_integration(
            db,
            company_id=company.id,
            integration_id=integration.id,
            payload=IntegrationUpdate(
                config={
                    "provider": "calendly",
                    "calendar_id": "primary",
                    "timezone": "America/Bogota",
                }
            ),
        )
    assert exc_info.value.status_code == 422
    assert "Calendar provider must be Google Calendar or Microsoft Calendar" in str(
        exc_info.value.detail
    )

    with pytest.raises(HTTPException) as exc_info:
        update_integration(
            db,
            company_id=company.id,
            integration_id=integration.id,
            payload=IntegrationUpdate(
                credentials="",
                config={
                    "provider": "google_calendar",
                    "calendar_id": "primary",
                    "timezone": "America/Bogota",
                },
            ),
        )
    assert exc_info.value.status_code == 422
    assert "Calendar credentials are required" in str(exc_info.value.detail)


def test_calendar_integration_is_tenant_scoped(db):
    company, _ = bootstrap_company(db, "Acme")
    other_company, _ = bootstrap_company(db, "Beta")

    integration = create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="calendar",
            credentials="calendar-secret",
            config={
                "provider": "google_calendar",
                "calendar_id": "primary",
                "timezone": "America/Bogota",
            },
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        update_integration(
            db,
            company_id=other_company.id,
            integration_id=integration.id,
            payload=IntegrationUpdate(
                config={
                    "provider": "microsoft_calendar",
                    "calendar_id": "primary",
                    "timezone": "America/Bogota",
                }
            ),
        )
    assert exc_info.value.status_code == 404


def test_calendar_appointment_syncs_on_create_and_update(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    db.add(contact)
    db.commit()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="calendar",
            credentials="calendar-secret",
            config={
                "provider": "microsoft_calendar",
                "calendar_id": "primary",
                "timezone": "America/Bogota",
                "api_base_url": "https://graph.microsoft.com/v1.0",
                "create_event_path": "me/calendars/{calendar_id}/events",
                "update_event_path": "me/events/{event_id}",
                "response_event_id_path": "id",
            },
        ),
    )

    requests: list[dict[str, object]] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload
            self.headers = {"Location": "https://graph.microsoft.com/v1.0/me/events/evt-001"}

        def json(self) -> dict[str, object]:
            return self._payload

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, method, url, json=None, headers=None):
            requests.append({"method": method, "url": url, "json": json, "headers": headers})
            if url.endswith("/freeBusy"):
                return FakeResponse(
                    {
                        "kind": "calendar#freeBusy",
                        "timeMin": json["timeMin"],
                        "timeMax": json["timeMax"],
                        "calendars": {"primary": {"busy": []}},
                    }
                )
            if url.endswith("/getSchedule"):
                return FakeResponse(
                    {
                        "value": [
                            {
                                "scheduleId": "primary",
                                "availabilityView": "0",
                                "scheduleItems": [],
                            }
                        ]
                    }
                )
            if method == "POST":
                return FakeResponse({"id": "evt-001"})
            return FakeResponse({"id": "evt-002"})

    monkeypatch.setattr("app.integrations.calendar.httpx.Client", FakeClient)

    appointment = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            scheduled_at=datetime(2026, 1, 15, 10, 30, tzinfo=UTC),
            duration_minutes=45,
            notes="Primera cita",
        ),
    )
    assert appointment.external_calendar_event_id == "evt-001"
    assert appointment.calendar_sync_status == "synced"
    assert appointment.calendar_synced_at is not None
    assert appointment.calendar_sync_obsolete_at is None

    updated = update_appointment(
        db,
        company_id=company.id,
        appointment_id=appointment.id,
        payload=AppointmentUpdate(notes="Cita reprogramada"),
    )
    assert updated.external_calendar_event_id == "evt-001"
    assert updated.calendar_sync_status == "synced"
    assert updated.calendar_synced_at is not None
    assert updated.calendar_sync_obsolete_at is None
    assert updated.notes == "Cita reprogramada"
    assert len(requests) == 3
    assert requests[0]["url"].endswith("/getSchedule")
    assert requests[0]["method"] == "POST"
    assert requests[1]["method"] == "POST"
    assert requests[2]["method"] == "PATCH"

    synced_events = list(
        db.scalars(
            select(Event).where(
                Event.company_id == company.id,
                Event.event_type == "appointment.calendar_synced",
            )
        )
    )
    assert len(synced_events) == 2


def test_calendar_appointment_failed_create_keeps_internal_appointment_committed(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    db.add(contact)
    db.commit()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="calendar",
            credentials="calendar-secret",
            config={
                "provider": "google_calendar",
                "calendar_id": "primary",
                "timezone": "America/Bogota",
                "api_base_url": "https://www.googleapis.com/calendar/v3",
                "create_event_path": "calendars/{calendar_id}/events",
                "update_event_path": "calendars/{calendar_id}/events/{event_id}",
                "response_event_id_path": "id",
            },
        ),
    )

    def failing_sync(*args, **kwargs):
        raise RuntimeError("calendar down")

    monkeypatch.setattr("app.appointments.service.sync_appointment_with_calendar", failing_sync)

    appointment = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            scheduled_at=datetime(2026, 1, 15, 10, 30, tzinfo=UTC),
            duration_minutes=45,
            notes="Primera cita",
        ),
    )

    assert appointment.id is not None
    assert appointment.calendar_sync_status == "failed"
    assert appointment.calendar_sync_error is not None
    assert "calendar down" in appointment.calendar_sync_error
    assert appointment.calendar_sync_obsolete_at is None
    assert appointment.external_calendar_event_id is None

    failed_events = list(
        db.scalars(
            select(Event).where(
                Event.company_id == company.id,
                Event.event_type == "appointment.calendar_sync_failed",
            )
        )
    )
    assert len(failed_events) == 1
    assert failed_events[0].payload["sync_status"] == "failed"
    assert failed_events[0].payload["external_calendar_event_id"] is None


def test_calendar_appointment_failed_resync_marks_appointment_obsolete(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    db.add(contact)
    db.commit()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="calendar",
            credentials="calendar-secret",
            config={
                "provider": "google_calendar",
                "calendar_id": "primary",
                "timezone": "America/Bogota",
                "api_base_url": "https://www.googleapis.com/calendar/v3",
                "create_event_path": "calendars/{calendar_id}/events",
                "update_event_path": "calendars/{calendar_id}/events/{event_id}",
                "response_event_id_path": "id",
            },
        ),
    )

    calls: list[str] = []

    class SuccessfulThenFailingClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, method, url, json=None, headers=None):
            calls.append(method)
            if url.endswith("/freeBusy"):
                return SimpleNamespace(
                    headers={},
                    json=lambda: {
                        "kind": "calendar#freeBusy",
                        "timeMin": json["timeMin"],
                        "timeMax": json["timeMax"],
                        "calendars": {"primary": {"busy": []}},
                    },
                    raise_for_status=lambda: None,
                )
            if len(calls) == 2:
                return SimpleNamespace(
                    headers={"Location": "https://www.googleapis.com/calendar/v3/calendars/primary/events/evt-123"},
                    json=lambda: {"id": "evt-123"},
                    raise_for_status=lambda: None,
                )
            raise httpx.ConnectError(
                "calendar down",
                request=httpx.Request(method, url),
            )

    monkeypatch.setattr("app.integrations.calendar.httpx.Client", SuccessfulThenFailingClient)

    appointment = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            scheduled_at=datetime(2026, 1, 15, 11, 0, tzinfo=UTC),
            duration_minutes=30,
            notes="Cita inicial",
        ),
    )
    assert appointment.external_calendar_event_id == "evt-123"
    assert appointment.calendar_sync_status == "synced"
    assert appointment.calendar_synced_at is not None
    assert appointment.calendar_sync_obsolete_at is None

    updated = update_appointment(
        db,
        company_id=company.id,
        appointment_id=appointment.id,
        payload=AppointmentUpdate(notes="Cita ajustada"),
    )
    assert updated.external_calendar_event_id == "evt-123"
    assert updated.calendar_sync_status == "obsolete"
    assert updated.calendar_sync_error
    assert "calendar down" in updated.calendar_sync_error
    assert updated.calendar_sync_obsolete_at is not None
    assert updated.notes == "Cita ajustada"
    assert len(calls) == 3

    failed_events = list(
        db.scalars(
            select(Event).where(
                Event.company_id == company.id,
                Event.event_type == "appointment.calendar_sync_failed",
            )
        )
    )
    assert len(failed_events) == 1
    assert failed_events[0].payload["sync_status"] == "obsolete"
    assert failed_events[0].payload["external_calendar_event_id"] == "evt-123"


def test_update_appointment_rejects_conflicting_slot(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    existing = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            scheduled_at=datetime(2026, 6, 30, 10, 0, tzinfo=UTC),
            duration_minutes=60,
            notes="Cita 1",
        ),
    )
    moving = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            scheduled_at=datetime(2026, 6, 30, 12, 0, tzinfo=UTC),
            duration_minutes=30,
            notes="Cita 2",
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        update_appointment(
            db,
            company_id=company.id,
            appointment_id=moving.id,
            payload=AppointmentUpdate(scheduled_at=datetime(2026, 6, 30, 10, 30, tzinfo=UTC)),
        )

    assert exc_info.value.status_code == 409
    assert list(
        db.scalars(
            select(Event).where(
                Event.company_id == company.id,
                Event.event_type == "appointment.updated",
            )
        )
    ) == []
    refreshed = db.get(Appointment, moving.id)
    assert refreshed is not None
    assert refreshed.scheduled_at == datetime(2026, 6, 30, 12, 0)


@pytest.mark.parametrize(
    ("provider", "response_payload", "expected_start"),
    [
        (
            "google_calendar",
            {
                "calendars": {
                    "primary": {
                        "busy": [
                            {
                                "start": "2026-01-16T08:00:00+00:00",
                                "end": "2026-01-16T10:00:00+00:00",
                            }
                        ]
                    }
                }
            },
            datetime(2026, 1, 16, 8, 0, tzinfo=UTC),
        ),
        (
            "microsoft_calendar",
            {
                "value": [
                    {
                        "scheduleItems": [
                            {
                                "start": {"dateTime": "2026-01-16T08:00:00", "timeZone": "America/New_York"},
                                "end": {"dateTime": "2026-01-16T10:00:00", "timeZone": "America/New_York"},
                                "status": "busy",
                            }
                        ]
                    }
                ]
            },
            datetime(2026, 1, 16, 13, 0, tzinfo=UTC),
        ),
    ],
)
def test_calendar_adapter_fetch_busy_intervals_parses_busy_slots(
    monkeypatch,
    provider,
    response_payload,
    expected_start,
):
    adapter = HttpCalendarAdapter(provider)
    config = normalize_calendar_config(
        {
            "provider": provider,
            "calendar_id": "primary",
            "timezone": "UTC",
        }
    )
    requests: list[tuple[str, str, dict[str, object] | None, dict[str, str] | None]] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload
            self.headers = {}

        def json(self) -> dict[str, object]:
            return self._payload

        def raise_for_status(self) -> None:
            return None

    def fake_request(self, method, url, json=None, headers=None):
        requests.append((method, url, json, headers))
        return FakeResponse(response_payload)

    monkeypatch.setattr("app.integrations.calendar.httpx.Client.request", fake_request)

    intervals = adapter.fetch_busy_intervals(
        company_id=uuid4(),
        time_min=datetime(2026, 1, 16, 0, 0, tzinfo=UTC),
        time_max=datetime(2026, 1, 17, 0, 0, tzinfo=UTC),
        config=config,
        credentials_raw="calendar-secret",
    )

    assert len(intervals) == 1
    assert intervals[0].start == expected_start
    assert intervals[0].end == expected_start + timedelta(hours=2)
    assert requests
    assert requests[0][0] == "POST"
    assert "calendar" in requests[0][1]
    assert requests[0][3]


def test_normalize_calendar_config_backfills_default_provider_defaults():
    config = normalize_calendar_config({"calendar_id": "primary"})

    assert config["provider"] == "google_calendar"
    assert config["availability_path"] == "freeBusy"
    assert config["api_base_url"] == "https://www.googleapis.com/calendar/v3"


def test_calendar_adapter_fetch_busy_intervals_raises_on_malformed_response(monkeypatch):
    adapter = HttpCalendarAdapter("google_calendar")
    config = normalize_calendar_config({"calendar_id": "primary", "timezone": "UTC"})

    class FakeResponse:
        def json(self) -> dict[str, object]:
            return {"calendars": {}}

        def raise_for_status(self) -> None:
            return None

    def fake_request(self, method, url, json=None, headers=None):
        return FakeResponse()

    monkeypatch.setattr("app.integrations.calendar.httpx.Client.request", fake_request)

    with pytest.raises(ValueError):
        adapter.fetch_busy_intervals(
            company_id=uuid4(),
            time_min=datetime(2026, 1, 16, 0, 0, tzinfo=UTC),
            time_max=datetime(2026, 1, 17, 0, 0, tzinfo=UTC),
            config=config,
            credentials_raw="calendar-secret",
        )


def test_calendar_adapter_fetch_busy_intervals_uses_provider_timezone_for_microsoft_request(monkeypatch):
    adapter = HttpCalendarAdapter("microsoft_calendar")
    config = normalize_calendar_config(
        {
            "provider": "microsoft_calendar",
            "calendar_id": "primary",
            "timezone": "America/New_York",
        }
    )
    requests: list[dict[str, object]] = []

    class FakeResponse:
        def json(self) -> dict[str, object]:
            return {
                "value": [
                    {
                        "scheduleItems": [
                            {
                                "start": {"dateTime": "2026-01-15T19:00:00", "timeZone": "America/New_York"},
                                "end": {"dateTime": "2026-01-15T20:00:00", "timeZone": "America/New_York"},
                                "status": "busy",
                            }
                        ]
                    }
                ]
            }

        def raise_for_status(self) -> None:
            return None

    def fake_request(self, method, url, json=None, headers=None):
        requests.append(json or {})
        return FakeResponse()

    monkeypatch.setattr("app.integrations.calendar.httpx.Client.request", fake_request)

    adapter.fetch_busy_intervals(
        company_id=uuid4(),
        time_min=datetime(2026, 1, 16, 0, 0, tzinfo=UTC),
        time_max=datetime(2026, 1, 17, 0, 0, tzinfo=UTC),
        config=config,
        credentials_raw="calendar-secret",
    )

    assert requests
    assert requests[0]["startTime"]["dateTime"] == "2026-01-15T19:00:00"
    assert requests[0]["startTime"]["timeZone"] == "America/New_York"
    assert requests[0]["endTime"]["dateTime"] == "2026-01-16T19:00:00"
    assert requests[0]["endTime"]["timeZone"] == "America/New_York"


def test_payment_link_ttl_applies_custom_and_default_values(db, monkeypatch):
    captured_ttls: list[int] = []

    def fake_create_payment_link(**kwargs):
        expires_in_minutes = kwargs["expires_in_minutes"]
        captured_ttls.append(expires_in_minutes)
        reference = kwargs["reference"]
        return SimpleNamespace(
            url=f"https://checkout.example/{reference}",
            reference=reference,
            link_id=f"link-{reference[:8]}",
            expires_at=datetime.now(UTC) + timedelta(minutes=expires_in_minutes),
            raw={"reference": reference},
        )

    monkeypatch.setattr("app.payments.contract.create_wompi_payment_link", fake_create_payment_link)

    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    db.add(Inventory(company_id=company.id, product_id=product.id, quantity_available=5))
    db.commit()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="payments",
            credentials=json.dumps(
                {"private_key": "pk_test", "events_secret": "evt_test"}
            ),
            config={
                "provider": "wompi",
                "environment": "sandbox",
                "currency": "COP",
                "payment_link_ttl_minutes": "45",
            },
        ),
    )
    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)
    assert captured_ttls[-1] == 45
    assert order.payment_provider == "wompi"
    assert order.payment_link == f"https://checkout.example/{order.payment_reference}"

    company_default, _ = bootstrap_company(db, "Beta")
    contact_default = Contact(
        company_id=company_default.id,
        name="Cliente Beta",
        phone="573000000001",
    )
    product_default = Product(
        company_id=company_default.id,
        name="Pantalon",
        sku="PAN-01",
        price=Decimal("65000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-2",
        whatsapp_product_retailer_id="pan-01",
    )
    db.add_all([contact_default, product_default])
    db.flush()
    conversation_default = Conversation(
        company_id=company_default.id,
        contact_id=contact_default.id,
        status="open",
    )
    db.add(conversation_default)
    db.flush()
    db.add(
        Inventory(
            company_id=company_default.id,
            product_id=product_default.id,
            quantity_available=3,
        )
    )
    db.commit()

    create_integration(
        db,
        company_id=company_default.id,
        payload=IntegrationCreate(
            type="payments",
            credentials=json.dumps(
                {"private_key": "pk_beta", "events_secret": "evt_beta"}
            ),
            config={
                "provider": "wompi",
                "environment": "sandbox",
                "currency": "COP",
            },
        ),
    )
    order_default = create_order(
        db,
        company_id=company_default.id,
        payload=OrderCreate(
            contact_id=contact_default.id,
            conversation_id=conversation_default.id,
            items=[OrderItemCreate(product_id=product_default.id, quantity=1)],
        ),
    )
    order_default = generate_payment_link(
        db,
        company_id=company_default.id,
        order_id=order_default.id,
    )
    assert captured_ttls[-1] == 120
    assert order_default.payment_provider == "wompi"
    assert order_default.payment_link == f"https://checkout.example/{order_default.payment_reference}"


def test_mock_payment_provider_is_rejected_in_production(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    monkeypatch.setattr(
        "app.payments.contract.get_settings",
        lambda: SimpleNamespace(app_env="production"),
    )

    with pytest.raises(HTTPException) as exc_info:
        create_integration(
            db,
            company_id=company.id,
            payload=IntegrationCreate(
                type="payments",
                credentials=None,
                config={
                    "provider": "mock",
                    "environment": "sandbox",
                    "currency": "COP",
                },
            ),
        )

    assert exc_info.value.status_code == 422
    assert "Local payment provider is not allowed in production" in str(exc_info.value.detail)


def test_generate_payment_link_rejects_mock_provider_in_production(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    db.add(Inventory(company_id=company.id, product_id=product.id, quantity_available=5))
    db.commit()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="payments",
            credentials=None,
            config={
                "provider": "mock",
                "environment": "sandbox",
                "currency": "COP",
            },
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )

    monkeypatch.setattr(
        "app.payments.contract.get_settings",
        lambda: SimpleNamespace(app_env="production"),
    )

    with pytest.raises(HTTPException) as exc_info:
        generate_payment_link(db, company_id=company.id, order_id=order.id)

    assert exc_info.value.status_code == 422
    assert "Local payment provider is not allowed in production" in str(exc_info.value.detail)


@pytest.mark.parametrize("provider", ["stripe"])
def test_unsupported_payment_provider_is_rejected(db, provider):
    company, _ = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc_info:
        create_integration(
            db,
            company_id=company.id,
            payload=IntegrationCreate(
                type="payments",
                credentials=None,
                config={
                    "provider": provider,
                    "environment": "sandbox",
                    "currency": "COP",
                },
            ),
        )

    assert exc_info.value.status_code == 422
    assert "Unsupported payment provider" in str(exc_info.value.detail)


@pytest.mark.parametrize(
    "provider, expected_host",
    [
        ("mercado_pago", "sandbox.mercado-pago.example.test"),
        ("aval_pay", "sandbox.aval-pay.example.test"),
    ],
)
def test_supported_payment_providers_generate_sandbox_links(db, provider, expected_host):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    db.add(Inventory(company_id=company.id, product_id=product.id, quantity_available=5))
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider=provider, ttl_minutes=90)

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    assert order.payment_provider == provider
    assert order.payment_link == f"https://{expected_host}/pay/{order.payment_reference}"
    assert order.payment_status == "pending"


@pytest.mark.parametrize("provider", ["mercado_pago", "aval_pay"])
def test_supported_payment_providers_reject_invalid_credentials(db, provider):
    company, _ = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc_info:
        create_integration(
            db,
            company_id=company.id,
            payload=IntegrationCreate(
                type="payments",
                credentials=json.dumps({"private_key": "pk_test"}),
                config={
                    "provider": provider,
                    "environment": "sandbox",
                    "currency": "COP",
                },
            ),
        )

    assert exc_info.value.status_code == 422
    assert "Payment credentials are required" in str(exc_info.value.detail)


def test_payment_webhook_idempotency_ignores_duplicate_transaction_ids(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=5)
    db.add(inventory)
    db.commit()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="payments",
            credentials=json.dumps(
                {"private_key": "pk_test", "events_secret": "evt_test"}
            ),
            config={
                "provider": "wompi",
                "environment": "sandbox",
                "currency": "COP",
            },
        ),
    )

    monkeypatch.setattr("app.payments.contract.verify_event_checksum", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "app.payments.contract.create_wompi_payment_link",
        lambda **kwargs: SimpleNamespace(
            url=f"https://checkout.example/{kwargs['reference']}",
            reference=kwargs["reference"],
            link_id="link-123",
            expires_at=datetime.now(UTC) + timedelta(minutes=120),
            raw={"reference": kwargs["reference"]},
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=2)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    payload = {
        "data": {
            "transaction": {
                "id": "txn-123",
                "reference": order.payment_reference,
                "status": "approved",
                "payment_link_id": "link-123",
            }
        }
    }

    first = process_payment_webhook(db, provider="wompi", payload=payload, header_checksum="sig")
    assert first.status == "processed"
    assert inventory.quantity_available == 3
    assert inventory.quantity_reserved == 0

    second = process_payment_webhook(db, provider="wompi", payload=payload, header_checksum="sig")
    assert second.status == "ignored"
    assert inventory.quantity_available == 3
    assert inventory.quantity_reserved == 0

    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.metadata_json["payment"]["transaction_id"] == "txn-123"
    assert stored_order.metadata_json["payment"]["processed_transaction_ids"] == ["txn-123"]


def test_payment_webhook_rejects_invalid_wompi_checksum(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=5)
    db.add(inventory)
    db.commit()

    create_integration(
        db,
        company_id=company.id,
        payload=IntegrationCreate(
            type="payments",
            credentials=json.dumps(
                {"private_key": "pk_test", "events_secret": "evt_test"}
            ),
            config={
                "provider": "wompi",
                "environment": "sandbox",
                "currency": "COP",
            },
        ),
    )

    monkeypatch.setattr("app.payments.contract.verify_event_checksum", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        "app.payments.contract.create_wompi_payment_link",
        lambda **kwargs: SimpleNamespace(
            url=f"https://checkout.example/{kwargs['reference']}",
            reference=kwargs["reference"],
            link_id="link-123",
            expires_at=datetime.now(UTC) + timedelta(minutes=120),
            raw={"reference": kwargs["reference"]},
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=2)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    with pytest.raises(HTTPException) as exc_info:
        process_payment_webhook(
            db,
            provider="wompi",
            payload={
                "data": {
                    "transaction": {
                        "id": "txn-invalid",
                        "reference": order.payment_reference,
                        "status": "approved",
                        "payment_link_id": "link-123",
                    }
                }
            },
            header_checksum="sig",
        )

    assert exc_info.value.status_code == 401
    assert inventory.quantity_available == 5
    assert inventory.quantity_reserved == 2
    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.status == "waiting_payment"
    assert stored_order.payment_status == "pending"


@pytest.mark.parametrize("provider", ["mercado_pago", "aval_pay"])
def test_supported_payment_webhook_processes_approved_events(db, provider):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=5)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider=provider)

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=2)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    payload = {
        "payment_reference": order.payment_reference,
        "status": "approved",
        "provider": provider,
    }
    raw_body, signature = sign_payment_webhook(payload, f"evt_{provider}")

    response = process_payment_webhook(
        db,
        provider=provider,
        payload=payload,
        header_checksum=signature,
        raw_body=raw_body,
    )

    assert response.status == "processed"
    assert response.payment_reference == order.payment_reference
    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.status == "paid"
    assert stored_order.payment_status == "paid"
    assert inventory.quantity_available == 3
    assert inventory.quantity_reserved == 0


@pytest.mark.parametrize("provider", ["mercado_pago", "aval_pay"])
def test_supported_payment_webhook_ignores_duplicate_payment_link_id(db, provider):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=5)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider=provider)

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=2)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    first_payload = {
        "payment_reference": order.payment_reference,
        "status": "pending",
        "provider": provider,
        "payment_link_id": "link-123",
        "id": "txn-1",
    }
    first_raw_body, first_signature = sign_payment_webhook(first_payload, f"evt_{provider}")
    first = process_payment_webhook(
        db,
        provider=provider,
        payload=first_payload,
        header_checksum=first_signature,
        raw_body=first_raw_body,
    )
    assert first.status == "processed"
    assert inventory.quantity_available == 5
    assert inventory.quantity_reserved == 2

    second_payload = {
        "payment_reference": order.payment_reference,
        "status": "pending",
        "provider": provider,
        "payment_link_id": "link-123",
        "id": "txn-2",
    }
    second_raw_body, second_signature = sign_payment_webhook(second_payload, f"evt_{provider}")
    second = process_payment_webhook(
        db,
        provider=provider,
        payload=second_payload,
        header_checksum=second_signature,
        raw_body=second_raw_body,
    )
    assert second.status == "ignored"
    assert inventory.quantity_available == 5
    assert inventory.quantity_reserved == 2

    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.metadata_json["payment"]["processed_payment_link_ids"] == ["link-123"]


@pytest.mark.parametrize("provider", ["mercado_pago", "aval_pay"])
def test_supported_payment_webhook_requires_signature(db, provider):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="cam-neg",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=5)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider=provider)

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=2)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    payload = {
        "payment_reference": order.payment_reference,
        "status": "approved",
        "provider": provider,
    }
    raw_body, _ = sign_payment_webhook(payload, f"evt_{provider}")

    with pytest.raises(HTTPException) as exc_info:
        process_payment_webhook(
            db,
            provider=provider,
            payload=payload,
            raw_body=raw_body,
    )

    assert exc_info.value.status_code == 401
    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.status == "waiting_payment"
    assert stored_order.payment_status == "pending"


def test_mock_payment_webhook_ignores_duplicate_reference_without_transaction_id(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-01",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-01",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()
    bootstrap_payment_integration(db, company_id=company.id)

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    payload = {
        "payment_reference": order.payment_reference,
        "status": "paid",
        "provider": "mock",
    }

    first = process_payment_webhook(db, provider="mock", payload=payload)
    assert first.status == "processed"
    assert inventory.quantity_available == 3
    assert inventory.quantity_reserved == 0

    second = process_payment_webhook(db, provider="mock", payload=payload)
    assert second.status == "ignored"
    assert inventory.quantity_available == 3
    assert inventory.quantity_reserved == 0

    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.metadata_json["payment"]["processed_payment_references"] == [
        order.payment_reference
    ]


def test_payment_webhook_ignores_duplicate_expired_events_with_new_transaction_id(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-01",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-01",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()
    bootstrap_payment_integration(db, company_id=company.id)

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    first_payload = {
        "id": "txn-expired-1",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-123",
    }
    second_payload = {
        "id": "txn-expired-2",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-123",
    }

    first = process_payment_webhook(db, provider="mock", payload=first_payload)
    assert first.status == "processed"
    assert inventory.quantity_reserved == 0

    second = process_payment_webhook(db, provider="mock", payload=second_payload)
    assert second.status == "ignored"
    assert inventory.quantity_reserved == 0
    assert inventory.quantity_available == 4


def test_payment_webhook_ignores_late_expired_event_after_cancellation(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-01",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-01",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()
    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)
    cancelled = cancel_order(db, company_id=company.id, order_id=order.id)

    assert cancelled.status == "cancelled"
    assert inventory.quantity_reserved == 0
    assert inventory.quantity_available == 4

    response = process_payment_webhook(
        db,
        provider="mercado_pago",
        payload={
            "id": "txn-late-expired",
            "reference": order.payment_reference,
            "status": "expired",
            "payment_link_id": "link-123",
        },
        raw_body=json.dumps(
            {
                "id": "txn-late-expired",
                "reference": order.payment_reference,
                "status": "expired",
                "payment_link_id": "link-123",
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(
                {
                    "id": "txn-late-expired",
                    "reference": order.payment_reference,
                    "status": "expired",
                    "payment_link_id": "link-123",
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    assert response.status == "ignored"
    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.status == "cancelled"
    assert stored_order.payment_status == "cancelled"
    assert inventory.quantity_reserved == 0
    assert inventory.quantity_available == 4


def test_payment_webhook_ignores_mismatched_provider_for_same_reference(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Sudadera",
        sku="SUD-01",
        price=Decimal("95000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="sud-01",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=2)
    db.add(inventory)
    db.commit()
    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    payload = {
        "payment_reference": order.payment_reference,
        "status": "paid",
        "provider": "mercado_pago",
    }

    response = process_payment_webhook(db, provider="wompi", payload=payload)
    assert response.status == "ignored"
    assert inventory.quantity_available == 2
    assert inventory.quantity_reserved == 1

    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.status == "waiting_payment"


@pytest.mark.parametrize("payment_status", ["cancelled", "voided"])
def test_payment_webhook_cancels_order_and_releases_reserved_inventory(db, payment_status):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-01",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-01",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()
    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    response = process_payment_webhook(
        db,
        provider="mercado_pago",
        payload={
            "id": f"txn-{payment_status}",
            "reference": order.payment_reference,
            "status": payment_status,
            "payment_link_id": "link-123",
        },
        raw_body=json.dumps(
            {
                "id": f"txn-{payment_status}",
                "reference": order.payment_reference,
                "status": payment_status,
                "payment_link_id": "link-123",
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(
                {
                    "id": f"txn-{payment_status}",
                    "reference": order.payment_reference,
                    "status": payment_status,
                    "payment_link_id": "link-123",
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    assert response.status == "processed"
    assert response.payment_reference == order.payment_reference
    assert inventory.quantity_available == 4
    assert inventory.quantity_reserved == 0

    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.status == "cancelled"
    assert stored_order.payment_status == "cancelled"

    second = process_payment_webhook(
        db,
        provider="mercado_pago",
        payload={
            "id": f"txn-{payment_status}-retry",
            "reference": order.payment_reference,
            "status": payment_status,
            "payment_link_id": "link-123",
        },
        raw_body=json.dumps(
            {
                "id": f"txn-{payment_status}-retry",
                "reference": order.payment_reference,
                "status": payment_status,
                "payment_link_id": "link-123",
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(
                {
                    "id": f"txn-{payment_status}-retry",
                    "reference": order.payment_reference,
                    "status": payment_status,
                    "payment_link_id": "link-123",
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )
    assert second.status == "ignored"
    assert inventory.quantity_available == 4
    assert inventory.quantity_reserved == 0


def test_expired_payment_webhook_sends_single_ai_followup_and_persists_metadata(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-01",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-01",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")
    create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-1",
            business_account_id="waba-1",
            access_token="token-1",
            verify_token="verify-1",
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    follow_up_body = "Tu link vencio. Te ayudo a continuar con el pago."
    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: AutoReplyResult(reply_text=follow_up_body),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-followup-1"}]},
    )

    payload = {
        "id": "txn-expired-1",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-123",
    }
    response = process_payment_webhook(
        db,
        provider="mercado_pago",
        payload=payload,
        raw_body=json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    assert response.status == "processed"
    assert inventory.quantity_available == 4
    assert inventory.quantity_reserved == 0

    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.status == "expired"
    assert stored_order.payment_status == "expired"
    follow_up_metadata = stored_order.metadata_json["payment"]["expired_followup"]
    assert follow_up_metadata["sent_at"]
    assert follow_up_metadata["source"] == "ai_payment_expired_followup"
    assert follow_up_metadata["message_id"]

    follow_up_messages = [
        message
        for message in db.scalars(select(Message).where(Message.company_id == company.id))
        if isinstance(message.metadata_json, dict)
        and message.metadata_json.get("source") == "ai_payment_expired_followup"
    ]
    assert len(follow_up_messages) == 1
    assert follow_up_messages[0].content == follow_up_body
    assert follow_up_metadata["message_id"] == str(follow_up_messages[0].id)

    second = process_payment_webhook(
        db,
        provider="mercado_pago",
        payload={
            "id": "txn-expired-2",
            "reference": order.payment_reference,
            "status": "expired",
            "payment_link_id": "link-123",
        },
        raw_body=json.dumps(
            {
                "id": "txn-expired-2",
                "reference": order.payment_reference,
                "status": "expired",
                "payment_link_id": "link-123",
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(
                {
                    "id": "txn-expired-2",
                    "reference": order.payment_reference,
                    "status": "expired",
                    "payment_link_id": "link-123",
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )
    assert second.status == "ignored"
    follow_up_messages_after_retry = [
        message
        for message in db.scalars(select(Message).where(Message.company_id == company.id))
        if isinstance(message.metadata_json, dict)
        and message.metadata_json.get("source") == "ai_payment_expired_followup"
    ]
    assert len(follow_up_messages_after_retry) == 1


def test_customer_reply_after_expired_injects_payment_context_into_ai_reply(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-01",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-01",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")
    create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-2",
            business_account_id="waba-2",
            access_token="token-2",
            verify_token="verify-2",
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: AutoReplyResult(reply_text="Tu link vencio. Te ayudo a continuar."),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-followup-2"}]},
    )

    expired_payload = {
        "id": "txn-expired-context",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-456",
    }
    process_payment_webhook(
        db,
        provider="mercado_pago",
        payload=expired_payload,
        raw_body=json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    captured_kwargs: dict[str, object] = {}

    def capture_ai_reply(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return AutoReplyResult(reply_text="Claro, te ayudo a continuar con el pago.")

    monkeypatch.setattr("app.whatsapp.service.generate_auto_reply", capture_ai_reply)

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-2"},
                                "contacts": [
                                    {
                                        "wa_id": "573000000000",
                                        "profile": {"name": "Cliente Demo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-customer-reply-1",
                                        "from": "573000000000",
                                        "timestamp": "1710000000",
                                        "type": "text",
                                        "text": {"body": "Quiero seguir con el pago"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0
    assert "payment_context" in captured_kwargs
    payment_context = str(captured_kwargs["payment_context"])
    assert "Orden origen del vencimiento" in payment_context
    assert "Estado de orden origen: expired" in payment_context
    assert "Seguimiento automatico enviado: si" in payment_context


def test_expired_payment_followup_failure_releases_reservation_and_allows_retry(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000010")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-10",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-10",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")
    create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-10",
            business_account_id="waba-10",
            access_token="token-10",
            verify_token="verify-10",
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)
    db.refresh(order)

    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: AutoReplyResult(reply_text="Te ayudo a continuar con el pago."),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("meta down")),
    )

    response = send_expired_payment_followup(db, order=order)
    assert response is None
    db.refresh(order)
    assert inventory.quantity_reserved == 1
    assert "claimed_at" not in order.metadata_json["payment"]["expired_followup"]
    assert "sent_at" not in order.metadata_json["payment"]["expired_followup"]

    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-followup-retry"}]},
    )

    response_retry = send_expired_payment_followup(db, order=order)
    assert response_retry is not None
    db.refresh(order)
    follow_up_metadata = order.metadata_json["payment"]["expired_followup"]
    assert follow_up_metadata["sent_at"]
    assert response_retry.meta_message_id == "wamid-followup-retry"
    assert follow_up_metadata["message_id"] == str(response_retry.message_id)


def test_customer_reply_after_expired_can_start_a_new_payment_flow_from_backend(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000001")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-02",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-02",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")
    create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-3",
            business_account_id="waba-3",
            access_token="token-3",
            verify_token="verify-3",
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    follow_up_ids = iter(
        [
            "wamid-followup-new-flow-1",
            "wamid-followup-new-flow-2",
            "wamid-followup-new-flow-3",
        ]
    )
    captured_payment_contexts: list[str | None] = []

    def capture_ai_reply(*args, **kwargs):
        captured_payment_contexts.append(kwargs.get("payment_context"))
        return AutoReplyResult(reply_text="Perfecto, te comparto un nuevo link para continuar.")

    monkeypatch.setattr("app.whatsapp.service.generate_auto_reply", capture_ai_reply)
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": next(follow_up_ids)}]},
    )

    expired_payload = {
        "id": "txn-expired-new-flow",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-789",
    }
    process_payment_webhook(
        db,
        provider="mercado_pago",
        payload=expired_payload,
        raw_body=json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-3"},
                                "contacts": [
                                    {
                                        "wa_id": "573000000001",
                                        "profile": {"name": "Cliente Demo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-customer-reply-new-flow-1",
                                        "from": "573000000001",
                                        "timestamp": "1710000200",
                                        "type": "text",
                                        "text": {"body": "Quiero continuar con el pago"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0

    orders = list(
        db.scalars(
            select(Order)
            .where(Order.company_id == company.id, Order.conversation_id == conversation.id)
            .order_by(Order.created_at.asc())
        )
    )
    assert len(orders) == 2
    expired_order, recovery_order = orders
    assert expired_order.status == "expired"
    assert recovery_order.status == "waiting_payment"
    assert recovery_order.payment_link
    payment_metadata = recovery_order.metadata_json["payment"]
    follow_up_metadata = payment_metadata["followup"]
    assert follow_up_metadata["origin_order_id"] == str(expired_order.id)
    assert recovery_order.payment_provider == "mercado_pago"

    recovery_messages = [
        message
        for message in db.scalars(select(Message).where(Message.company_id == company.id))
        if isinstance(message.metadata_json, dict)
        and message.metadata_json.get("source") == "ai_payment_followup_recovery"
    ]
    assert len(recovery_messages) == 1
    assert recovery_order.payment_link in recovery_messages[0].content

    processed_again, skipped_again = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-3"},
                                "contacts": [
                                    {
                                        "wa_id": "573000000001",
                                        "profile": {"name": "Cliente Demo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-customer-reply-new-flow-2",
                                        "from": "573000000001",
                                        "timestamp": "1710000201",
                                        "type": "text",
                                        "text": {"body": "Quiero continuar con el pago"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed_again == 1
    assert skipped_again == 0
    orders_after_retry = list(
        db.scalars(
            select(Order)
            .where(Order.company_id == company.id, Order.conversation_id == conversation.id)
            .order_by(Order.created_at.asc())
        )
    )
    assert len(orders_after_retry) == 2
    assert captured_payment_contexts[-1] is not None
    assert "Orden origen del vencimiento" in captured_payment_contexts[-1]
    assert "Estado de orden origen: expired" in captured_payment_contexts[-1]
    assert "Seguimiento automatico enviado: si" in captured_payment_contexts[-1]


def test_customer_reply_after_expired_accepts_simple_affirmative_to_continue(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000004")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-05",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-05",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")
    create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-5",
            business_account_id="waba-5",
            access_token="token-5",
            verify_token="verify-5",
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: AutoReplyResult(reply_text="Perfecto, te comparto el link otra vez."),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-affirmative-continue"}]},
    )

    expired_payload = {
        "id": "txn-expired-affirmative",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-affirmative",
    }
    process_payment_webhook(
        db,
        provider="mercado_pago",
        payload=expired_payload,
        raw_body=json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-5"},
                                "contacts": [
                                    {
                                        "wa_id": "573000000004",
                                        "profile": {"name": "Cliente Demo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-customer-reply-affirmative",
                                        "from": "573000000004",
                                        "timestamp": "1710000300",
                                        "type": "text",
                                        "text": {"body": "Sí, por favor"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0
    orders = list(
        db.scalars(
            select(Order)
            .where(Order.company_id == company.id, Order.conversation_id == conversation.id)
            .order_by(Order.created_at.asc())
        )
    )
    assert len(orders) == 2
    assert orders[1].payment_link


def test_customer_reply_after_expired_accepts_helpful_phrase_to_continue(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000006")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-07",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-07",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")
    create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-7",
            business_account_id="waba-7",
            access_token="token-7",
            verify_token="verify-7",
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: AutoReplyResult(reply_text="Perfecto, te ayudo a continuar."),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-helpful-continue"}]},
    )

    expired_payload = {
        "id": "txn-expired-helpful",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-helpful",
    }
    process_payment_webhook(
        db,
        provider="mercado_pago",
        payload=expired_payload,
        raw_body=json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-7"},
                                "contacts": [
                                    {
                                        "wa_id": "573000000006",
                                        "profile": {"name": "Cliente Demo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-customer-reply-helpful",
                                        "from": "573000000006",
                                        "timestamp": "1710000401",
                                        "type": "text",
                                        "text": {"body": "Necesito ayuda para seguir pagando"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0
    orders = list(
        db.scalars(
            select(Order)
            .where(Order.company_id == company.id, Order.conversation_id == conversation.id)
            .order_by(Order.created_at.asc())
        )
    )
    assert len(orders) == 2
    assert orders[1].payment_link


def test_customer_reply_after_expired_can_surface_products_when_ai_requests_more_options(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000005")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-06",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-06",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")
    create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-6",
            business_account_id="waba-6",
            access_token="token-6",
            verify_token="verify-6",
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: AutoReplyResult(
            reply_text="Te comparto el link y más opciones.",
            product_retailer_ids=[product.whatsapp_product_retailer_id],
        ),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-products-after-recovery"}]},
    )
    captured_cards = {}

    def fake_send_product_cards_from_db(*_args, **kwargs):
        captured_cards["payload"] = kwargs["payload"]
        return SimpleNamespace(message_id=None)

    monkeypatch.setattr(
        "app.whatsapp.service.send_product_cards_from_db",
        fake_send_product_cards_from_db,
    )

    expired_payload = {
        "id": "txn-expired-products",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-products",
    }
    process_payment_webhook(
        db,
        provider="mercado_pago",
        payload=expired_payload,
        raw_body=json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-6"},
                                "contacts": [
                                    {
                                        "wa_id": "573000000005",
                                        "profile": {"name": "Cliente Demo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-customer-reply-products",
                                        "from": "573000000005",
                                        "timestamp": "1710000400",
                                        "type": "text",
                                        "text": {"body": "Quiero continuar y ver más opciones"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0
    assert "payload" in captured_cards
    assert captured_cards["payload"].product_ids == [product.id]


def test_customer_reply_with_support_request_does_not_create_recovery_order(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000003")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-04",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-04",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")
    create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-4",
            business_account_id="waba-4",
            access_token="token-4",
            verify_token="verify-4",
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: AutoReplyResult(reply_text="Te conecto con un asesor."),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-support-request"}]},
    )

    expired_payload = {
        "id": "txn-expired-support",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-456",
    }
    process_payment_webhook(
        db,
        provider="mercado_pago",
        payload=expired_payload,
        raw_body=json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-4"},
                                "contacts": [
                                    {
                                        "wa_id": "573000000003",
                                        "profile": {"name": "Cliente Demo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-support-request-1",
                                        "from": "573000000003",
                                        "timestamp": "1710000400",
                                        "type": "text",
                                        "text": {"body": "Quiero hablar con un asesor"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0

    orders = list(
        db.scalars(
            select(Order)
            .where(Order.company_id == company.id, Order.conversation_id == conversation.id)
            .order_by(Order.created_at.asc())
        )
    )
    assert len(orders) == 1
    assert orders[0].status == "expired"
    support_messages = [
        message
        for message in db.scalars(select(Message).where(Message.company_id == company.id))
        if isinstance(message.metadata_json, dict)
        and message.metadata_json.get("source") == "ai_payment_followup_recovery"
    ]
    assert support_messages == []


def test_customer_reply_after_expired_retries_recovery_order_when_link_generation_fails_once(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000002")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-03",
        price=Decimal("35000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="gor-03",
    )
    db.add_all([contact, product])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id, status="open")
    db.add(conversation)
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    bootstrap_payment_integration(db, company_id=company.id, provider="mercado_pago")
    create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-4",
            business_account_id="waba-4",
            access_token="token-4",
            verify_token="verify-4",
        ),
    )

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: AutoReplyResult(reply_text="Perfecto, te comparto un nuevo link."),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-recovery-fail"}]},
    )
    generate_payment_link_calls = iter(
        [
            RuntimeError("payment link failed"),
            None,
        ]
    )

    def fail_once_then_succeed(*args, **kwargs):
        outcome = next(generate_payment_link_calls)
        if isinstance(outcome, Exception):
            raise outcome
        return generate_payment_link(*args, **kwargs)

    monkeypatch.setattr(
        "app.orders.service.generate_payment_link",
        fail_once_then_succeed,
    )

    expired_payload = {
        "id": "txn-expired-recovery-fail",
        "reference": order.payment_reference,
        "status": "expired",
        "payment_link_id": "link-900",
    }
    process_payment_webhook(
        db,
        provider="mercado_pago",
        payload=expired_payload,
        raw_body=json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        header_checksum="sha256="
        + hmac.new(
            b"evt_mercado_pago",
            json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-4"},
                                "contacts": [
                                    {
                                        "wa_id": "573000000002",
                                        "profile": {"name": "Cliente Demo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-customer-reply-recovery-fail",
                                        "from": "573000000002",
                                        "timestamp": "1710000202",
                                        "type": "text",
                                        "text": {"body": "Quiero continuar con el pago"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0
    orders = list(
        db.scalars(
            select(Order)
            .where(Order.company_id == company.id, Order.conversation_id == conversation.id)
            .order_by(Order.created_at.asc())
        )
    )
    assert len(orders) == 2
    assert {order.status for order in orders} == {"expired", "pending"}
    recovery_order = next(order for order in orders if order.status == "pending")
    assert recovery_order.payment_link is None
    recovery_messages = [
        message
        for message in db.scalars(select(Message).where(Message.company_id == company.id))
        if isinstance(message.metadata_json, dict)
        and message.metadata_json.get("source") == "ai_payment_followup_recovery"
    ]
    assert recovery_messages == []
    generic_messages = [
        message
        for message in db.scalars(select(Message).where(Message.company_id == company.id))
        if isinstance(message.metadata_json, dict)
        and message.metadata_json.get("source") == "ai_auto_reply"
    ]
    assert generic_messages == []

    processed_retry, skipped_retry = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-4"},
                                "contacts": [
                                    {
                                        "wa_id": "573000000002",
                                        "profile": {"name": "Cliente Demo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-customer-reply-recovery-fail-2",
                                        "from": "573000000002",
                                        "timestamp": "1710000203",
                                        "type": "text",
                                        "text": {"body": "Quiero continuar con el pago"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed_retry == 1
    assert skipped_retry == 0
    db.refresh(recovery_order)
    assert recovery_order.status == "waiting_payment"
    assert recovery_order.payment_link
    recovery_messages_after_retry = [
        message
        for message in db.scalars(select(Message).where(Message.company_id == company.id))
        if isinstance(message.metadata_json, dict)
        and message.metadata_json.get("source") == "ai_payment_followup_recovery"
    ]
    assert len(recovery_messages_after_retry) == 1


def test_inventory_listing_only_creates_rows_for_meta_synced_products(db):
    company, _ = bootstrap_company(db, "Acme")
    synced_product = Product(
        company_id=company.id,
        name="Bronceador profesional",
        sku="BRONCE-01",
        price=Decimal("130000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="bronce-01-meta",
    )
    local_product = Product(
        company_id=company.id,
        name="Curso presencial",
        sku="CURSO-01",
        price=Decimal("250000.00"),
        currency="COP",
    )
    db.add_all([synced_product, local_product])
    db.commit()

    rows = list_inventory(db, company_id=company.id, limit=50, offset=0)

    assert len(rows) == 1
    assert rows[0].product_id == synced_product.id
    assert rows[0].quantity_available == 0
    assert rows[0].quantity_reserved == 0
    assert rows[0].available_units == 0
    assert available_units(rows[0]) == 0

    serialized = InventoryRead.model_validate(rows[0])
    assert serialized.available_units == 0


def test_inventory_mutations_reject_products_without_meta_sync(db):
    company, _ = bootstrap_company(db, "Acme")
    product = Product(
        company_id=company.id,
        name="Curso presencial",
        sku="CURSO-01",
        price=Decimal("250000.00"),
        currency="COP",
    )
    db.add(product)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        upsert_inventory(
            db,
            company_id=company.id,
            product_id=product.id,
            payload=InventoryUpdate(quantity_available=5, quantity_reserved=1),
        )
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        adjust_inventory(
            db,
            company_id=company.id,
            product_id=product.id,
            payload=InventoryAdjustment(delta_available=1, delta_reserved=0),
        )
    assert exc_info.value.status_code == 404


def test_ai_catalog_context_includes_real_inventory_availability(db):
    company, _ = bootstrap_company(db, "Acme")
    product = Product(
        company_id=company.id,
        name="Top Bronce 250ml",
        description="Bronceador profesional para camara y sol.",
        sku="TOP-250",
        price=Decimal("130000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="top-250-meta",
    )
    db.add(product)
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=product.id,
            quantity_available=6,
            quantity_reserved=2,
        )
    )
    db.commit()

    context = _build_catalog_context(db, company_id=company.id)

    assert "Top Bronce 250ml" in context
    assert "Meta retailer_id: top-250-meta" in context
    assert "Descripcion: Bronceador profesional para camara y sol." in context
    assert "Stock real disponible: 4" in context
    assert "stock: 6, reservado: 2" in context


def test_ai_catalog_context_skips_non_meta_products(db):
    company, _ = bootstrap_company(db, "Acme")
    synced_product = Product(
        company_id=company.id,
        name="Top Bronce 250ml",
        description="Bronceador profesional para camara y sol.",
        sku="TOP-250",
        price=Decimal("130000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="top-250-meta",
    )
    local_product = Product(
        company_id=company.id,
        name="Curso presencial",
        description="Producto local no ordenable",
        sku="CURSO-01",
        price=Decimal("500000.00"),
        currency="COP",
    )
    db.add_all([synced_product, local_product])
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=synced_product.id,
            quantity_available=6,
            quantity_reserved=2,
        )
    )
    db.add(
        Inventory(
            company_id=company.id,
            product_id=local_product.id,
            quantity_available=5,
            quantity_reserved=0,
        )
    )
    db.commit()

    context = _build_catalog_context(db, company_id=company.id)

    assert "Top Bronce 250ml" in context
    assert "Curso presencial" not in context


def test_ai_search_products_tool_skips_non_meta_products(db):
    company, _ = bootstrap_company(db, "Acme")
    synced_product = Product(
        company_id=company.id,
        name="Top Bronce 250ml",
        price=Decimal("130000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="top-250-meta",
    )
    local_product = Product(
        company_id=company.id,
        name="Curso presencial",
        price=Decimal("500000.00"),
        currency="COP",
    )
    db.add_all([synced_product, local_product])
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=synced_product.id,
            quantity_available=3,
            quantity_reserved=1,
        )
    )
    db.add(
        Inventory(
            company_id=company.id,
            product_id=local_product.id,
            quantity_available=10,
            quantity_reserved=0,
        )
    )
    db.commit()

    result = search_products_tool(db, company_id=company.id, query="Top")

    assert [product.id for product in result.products] == [synced_product.id]


def test_ai_search_products_tool_searches_meta_products_before_paging(db):
    company, _ = bootstrap_company(db, "Acme")
    synced_product = Product(
        company_id=company.id,
        name="Top Bronce 250ml",
        price=Decimal("130000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="top-250-meta",
    )
    db.add(synced_product)
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=synced_product.id,
            quantity_available=3,
            quantity_reserved=1,
        )
    )
    for index in range(12):
        db.add(
            Product(
                company_id=company.id,
                name=f"Top Local {index + 1}",
                price=Decimal("10000.00"),
                currency="COP",
            )
        )
    db.commit()

    result = search_products_tool(db, company_id=company.id, query="Top")

    assert [product.id for product in result.products] == [synced_product.id]


def test_check_stock_tool_rejects_non_meta_products(db):
    company, _ = bootstrap_company(db, "Acme")
    product = Product(
        company_id=company.id,
        name="Curso presencial",
        price=Decimal("500000.00"),
        currency="COP",
    )
    db.add(product)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        check_stock_tool(db, company_id=company.id, product_id=product.id, quantity=1)

    assert exc_info.value.status_code == 404


def test_ai_product_cards_only_use_available_meta_products_in_requested_order(db):
    company, _ = bootstrap_company(db, "Acme")
    available_first = Product(
        company_id=company.id,
        name="Top Bronce 250ml",
        price=Decimal("130000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="top-250-meta",
    )
    available_second = Product(
        company_id=company.id,
        name="Oleo 220ml",
        price=Decimal("70000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="oleo-220-meta",
    )
    out_of_stock = Product(
        company_id=company.id,
        name="Parafina 900ml",
        price=Decimal("220000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="parafina-900-meta",
    )
    without_meta_mapping = Product(
        company_id=company.id,
        name="Curso presencial",
        price=Decimal("500000.00"),
        currency="COP",
    )
    db.add_all([available_first, available_second, out_of_stock, without_meta_mapping])
    db.flush()
    db.add_all(
        [
            Inventory(
                company_id=company.id,
                product_id=available_first.id,
                quantity_available=3,
            ),
            Inventory(
                company_id=company.id,
                product_id=available_second.id,
                quantity_available=2,
            ),
            Inventory(
                company_id=company.id,
                product_id=out_of_stock.id,
                quantity_available=1,
                quantity_reserved=1,
            ),
            Inventory(
                company_id=company.id,
                product_id=without_meta_mapping.id,
                quantity_available=5,
            ),
        ]
    )
    db.commit()

    product_ids = _resolve_available_product_ids(
        db,
        company_id=company.id,
        retailer_ids=[
            "oleo-220-meta",
            "parafina-900-meta",
            "top-250-meta",
            "oleo-220-meta",
            "inventado",
        ],
    )

    assert product_ids == [available_second.id, available_first.id]
    assert _list_available_product_ids(db, company_id=company.id) == [
        available_second.id,
        available_first.id,
    ]
    assert _interactive_reply_requests_catalog({"title": "Productos"})
    assert _interactive_reply_requests_catalog({"title": "Ver catálogo"})
    assert not _interactive_reply_requests_catalog({"title": "Agenda tu cita"})


def test_product_query_sync_refreshes_catalog_inventory_and_deactivates_removed_products(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    removed = Product(
        company_id=company.id,
        name="Producto anterior",
        price=Decimal("90000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="removed-meta",
    )
    db.add(removed)
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=removed.id,
            quantity_available=7,
        )
    )
    db.commit()
    account = SimpleNamespace(
        company_id=company.id,
        business_account_id="waba-1",
        access_token_encrypted="encrypted-token",
    )
    monkeypatch.setattr(
        "app.whatsapp.service._fetch_catalog_product_rows",
        lambda **_kwargs: [
            {
                "retailer_id": "top-250-meta",
                "name": "Top Bronce 250ml",
                "description": "Bronceador profesional.",
                "price": "$ 130.000",
                "currency": "COP",
                "availability": "in stock",
                "inventory": 4,
                "image_url": "https://example.com/top.jpg",
                "url": "https://example.com/top",
                "visibility": "published",
            }
        ],
    )
    monkeypatch.setattr(
        "app.whatsapp.service._catalog_link_warning",
        lambda **_kwargs: None,
    )

    result = _sync_catalog_products_with_account(
        db,
        company_id=company.id,
        account=account,
        catalog_id="catalog-1",
    )

    synced = db.scalar(
        select(Product).where(
            Product.company_id == company.id,
            Product.whatsapp_product_retailer_id == "top-250-meta",
        )
    )
    synced_inventory = db.scalar(
        select(Inventory).where(Inventory.product_id == synced.id)
    )
    db.refresh(removed)
    removed_inventory = db.scalar(
        select(Inventory).where(Inventory.product_id == removed.id)
    )
    assert result.fetched == 1
    assert result.created == 1
    assert synced.price == Decimal("130000.00")
    assert synced_inventory.quantity_available == 4
    assert synced.metadata_json["image_url"] == "https://example.com/top.jpg"
    assert removed.status == "inactive"
    assert removed_inventory.quantity_available == 0


def test_product_query_sync_skips_rows_with_invalid_price_without_inventing_value(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    account = SimpleNamespace(
        company_id=company.id,
        business_account_id="waba-1",
        access_token_encrypted="encrypted-token",
    )
    monkeypatch.setattr(
        "app.whatsapp.service._fetch_catalog_product_rows",
        lambda **_kwargs: [
            {
                "retailer_id": "bad-price-meta",
                "name": "Producto sin precio valido",
                "description": "Meta devolvio un precio invalido.",
                "price": "0",
                "currency": "COP",
                "availability": "in stock",
                "inventory": 4,
            },
            {
                "retailer_id": "valid-price-meta",
                "name": "Producto valido",
                "description": "Meta devolvio un precio valido.",
                "price": "$ 130.000",
                "currency": "COP",
                "availability": "in stock",
                "inventory": 2,
            },
        ],
    )
    monkeypatch.setattr(
        "app.whatsapp.service._catalog_link_warning",
        lambda **_kwargs: None,
    )

    result = _sync_catalog_products_with_account(
        db,
        company_id=company.id,
        account=account,
        catalog_id="catalog-1",
    )

    invalid_product = db.scalar(
        select(Product).where(
            Product.company_id == company.id,
            Product.whatsapp_product_retailer_id == "bad-price-meta",
        )
    )
    valid_product = db.scalar(
        select(Product).where(
            Product.company_id == company.id,
            Product.whatsapp_product_retailer_id == "valid-price-meta",
        )
    )
    valid_inventory = db.scalar(select(Inventory).where(Inventory.product_id == valid_product.id))

    assert result.fetched == 2
    assert result.created == 1
    assert invalid_product is None
    assert valid_product is not None
    assert valid_product.price == Decimal("130000.00")
    assert valid_inventory.quantity_available == 2
    assert "precio invalido" in (result.warning or "")


def test_product_query_sync_preserves_existing_synced_product_when_meta_price_is_invalid(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    existing = Product(
        company_id=company.id,
        name="Producto existente",
        description="Catalogo previo",
        price=Decimal("99000.00"),
        currency="COP",
        status="active",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="existing-meta",
    )
    db.add(existing)
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=existing.id,
            quantity_available=5,
            quantity_reserved=1,
        )
    )
    db.commit()
    account = SimpleNamespace(
        company_id=company.id,
        business_account_id="waba-1",
        access_token_encrypted="encrypted-token",
    )
    monkeypatch.setattr(
        "app.whatsapp.service._fetch_catalog_product_rows",
        lambda **_kwargs: [
            {
                "retailer_id": "existing-meta",
                "name": "Producto existente actualizado",
                "description": "Meta devolvio precio invalido.",
                "price": "0",
                "currency": "COP",
                "availability": "in stock",
                "inventory": 8,
            }
        ],
    )
    monkeypatch.setattr(
        "app.whatsapp.service._catalog_link_warning",
        lambda **_kwargs: None,
    )

    result = _sync_catalog_products_with_account(
        db,
        company_id=company.id,
        account=account,
        catalog_id="catalog-1",
    )

    db.refresh(existing)
    inventory = db.scalar(select(Inventory).where(Inventory.product_id == existing.id))

    assert result.fetched == 1
    assert result.updated == 0
    assert existing.name == "Producto existente"
    assert existing.price == Decimal("99000.00")
    assert existing.status == "inactive"
    assert inventory.quantity_available == 0
    assert inventory.quantity_reserved == 1
    assert "precio invalido" in (result.warning or "")


def test_webhook_status_backfill_uses_latest_message_sent_event(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    account = WhatsAppAccount(
        company_id=company.id,
        phone_number_id="phone-1",
        business_account_id="waba-1",
        access_token_encrypted="encrypted",
        verify_token="verify",
    )
    contact_one = Contact(company_id=company.id, name="Cliente 1", phone="573001112233")
    contact_two = Contact(company_id=company.id, name="Cliente 2", phone="573001112234")
    db.add_all([account, contact_one, contact_two])
    db.flush()
    conversation_one = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact_one.id, channel="whatsapp"),
    )
    conversation_two = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact_two.id, channel="whatsapp"),
    )
    event_one = create_event(
        db,
        company_id=company.id,
        event_type="message.sent",
        payload={
            "conversation_id": str(conversation_one.id),
            "meta_message_id": "wamid-delivery-1",
        },
    )
    event_two = create_event(
        db,
        company_id=company.id,
        event_type="message.sent",
        payload={
            "conversation_id": str(conversation_two.id),
            "meta_message_id": "wamid-delivery-1",
        },
    )
    event_one.created_at = datetime(2026, 7, 4, 12, 0, tzinfo=UTC)
    event_two.created_at = datetime(2026, 7, 4, 12, 0, 1, tzinfo=UTC)
    db.commit()

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": account.phone_number_id},
                                "statuses": [
                                    {
                                        "id": "wamid-delivery-1",
                                        "status": "delivered",
                                        "recipient_id": "573001112233",
                                        "timestamp": "1710000000",
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0
    status_event = db.scalar(
        select(Event).where(
            Event.company_id == company.id,
            Event.event_type == "message.status",
            Event.payload["message_id"].as_string() == "wamid-delivery-1",
        )
    )
    assert status_event is not None
    assert status_event.payload["conversation_id"] == str(conversation_two.id)


def test_webhook_ai_reply_aborts_before_send_when_conversation_gets_paused_after_generation(
    db, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    account = WhatsAppAccount(
        company_id=company.id,
        phone_number_id="phone-2",
        business_account_id="waba-2",
        access_token_encrypted="encrypted",
        verify_token="verify",
    )
    contact = Contact(company_id=company.id, name="Cliente", phone="573001112235")
    db.add_all([account, contact])
    db.commit()

    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: AutoReplyResult(reply_text="Te respondo enseguida."),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._load_conversation_ai_enabled",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-1"}]},
    )

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": account.phone_number_id},
                                "messages": [
                                    {
                                        "id": "wamid-1",
                                        "from": "573001112235",
                                        "timestamp": "1710000000",
                                        "type": "text",
                                        "text": {"body": "Hola"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0
    sent_event = db.scalar(
        select(Event).where(
            Event.company_id == company.id,
            Event.event_type == "message.sent",
            Event.payload["source"].as_string() == "ai_auto_reply",
        )
    )
    assert sent_event is None


def test_product_query_detection_inventory_and_fallback_use_available_catalog_data(db):
    company, _ = bootstrap_company(db, "Acme")
    product = Product(
        company_id=company.id,
        name="Top Bronce 250ml",
        description="Bronceador profesional para cámara y sol.",
        price=Decimal("130000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="top-250-meta",
    )
    db.add(product)
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=product.id,
            quantity_available=5,
            quantity_reserved=1,
        )
    )
    db.commit()

    body = _build_available_products_fallback(
        db,
        company_id=company.id,
        product_ids=[product.id],
        intro="Te comparto opciones disponibles.",
    )

    assert _message_requests_catalog("Quiero ver bronceadores", None)
    assert _message_requests_catalog("", {"title": "Productos"})
    assert not _message_requests_catalog("Quiero agendar una cita", None)
    assert _meta_inventory_quantity({"inventory": "8"}, availability="in stock") == 8
    assert _meta_inventory_quantity({"inventory": 8}, availability="out of stock") == 0
    assert "Top Bronce 250ml: $130.000 COP" in body
    assert "Disponible (4 unidades)" in body


def test_webhook_forces_product_cards_when_product_button_selected(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    account = WhatsAppAccount(
        company_id=company.id,
        phone_number_id="phone-1",
        business_account_id="waba-1",
        access_token_encrypted="encrypted",
        verify_token="verify",
    )
    product = Product(
        company_id=company.id,
        name="Top Bronce 250ml",
        price=Decimal("130000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="top-250-meta",
    )
    db.add_all([account, product])
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=product.id,
            quantity_available=3,
        )
    )
    db.commit()
    captured = {}

    monkeypatch.setattr(
        "app.whatsapp.service._sync_linked_catalogs_for_product_query",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *_args, **_kwargs: AutoReplyResult(
            reply_text="Te comparto productos destacados.",
        ),
    )

    def fake_send_product_cards_from_db(*_args, **kwargs):
        captured["payload"] = kwargs["payload"]
        return SimpleNamespace(message_id=None)

    monkeypatch.setattr(
        "app.whatsapp.service.send_product_cards_from_db",
        fake_send_product_cards_from_db,
    )
    monkeypatch.setattr(
        "app.whatsapp.service._send_text_with_account",
        lambda *_args, **_kwargs: pytest.fail("No debe enviar texto si hay cards disponibles"),
    )

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-1"},
                                "contacts": [{"wa_id": "573001112233", "profile": {"name": "Camilo"}}],
                                "messages": [
                                    {
                                        "from": "573001112233",
                                        "id": "wamid-productos",
                                        "type": "interactive",
                                        "interactive": {
                                            "type": "button_reply",
                                            "button_reply": {
                                                "id": "menu_principal_opt_2",
                                                "title": "Productos",
                                            },
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0
    assert captured["payload"].product_ids == [product.id]
    assert captured["payload"].to == "573001112233"


def test_webhook_sends_product_image_cards_when_meta_catalog_cards_fail(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    account = WhatsAppAccount(
        company_id=company.id,
        phone_number_id="phone-1",
        business_account_id="waba-1",
        access_token_encrypted="encrypted",
        verify_token="verify",
    )
    product = Product(
        company_id=company.id,
        name="Top Bronce 250ml",
        price=Decimal("130000.00"),
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="top-250-meta",
        metadata_json={"image_url": "https://example.com/top.jpg"},
    )
    db.add_all([account, product])
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=product.id,
            quantity_available=3,
        )
    )
    db.commit()
    captured = {}

    monkeypatch.setattr(
        "app.whatsapp.service._sync_linked_catalogs_for_product_query",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *_args, **_kwargs: AutoReplyResult(
            reply_text="Te comparto productos destacados.",
        ),
    )
    monkeypatch.setattr(
        "app.whatsapp.service.send_product_cards_from_db",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HTTPException(status_code=502, detail="(#131009) Please check your catalog")
        ),
    )

    def fake_send_product_image_cards_from_db(*_args, **kwargs):
        captured["product_ids"] = kwargs["product_ids"]
        captured["to"] = kwargs["to"]
        return True

    monkeypatch.setattr(
        "app.whatsapp.service._send_product_image_cards_from_db",
        fake_send_product_image_cards_from_db,
    )
    monkeypatch.setattr(
        "app.whatsapp.service._send_text_with_account",
        lambda *_args, **_kwargs: pytest.fail("No debe caer a texto si envio tarjetas visuales"),
    )

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-1"},
                                "contacts": [{"wa_id": "573001112233", "profile": {"name": "Camilo"}}],
                                "messages": [
                                    {
                                        "from": "573001112233",
                                        "id": "wamid-productos-fallback",
                                        "type": "interactive",
                                        "interactive": {
                                            "type": "button_reply",
                                            "button_reply": {
                                                "id": "menu_principal_opt_2",
                                                "title": "Productos",
                                            },
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert processed == 1
    assert skipped == 0
    assert captured["product_ids"] == [product.id]
    assert captured["to"] == "573001112233"


def test_whatsapp_catalog_link_warning_detects_catalog_not_connected_to_waba(monkeypatch):
    account = SimpleNamespace(
        business_account_id="waba-1",
        access_token_encrypted="encrypted-token",
    )
    monkeypatch.setattr("app.whatsapp.service.decrypt_secret", lambda _value: "token")
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *_args, **_kwargs: {"data": [{"id": "catalog-connected"}]},
    )

    warning = _catalog_link_warning(account=account, catalog_id="catalog-missing")

    assert warning is not None
    assert "catalog-missing" in warning
    assert "waba-1" in warning
    assert "WhatsApp Manager" in warning


def test_whatsapp_catalog_link_warning_accepts_connected_catalog(monkeypatch):
    account = SimpleNamespace(
        business_account_id="waba-1",
        access_token_encrypted="encrypted-token",
    )
    monkeypatch.setattr("app.whatsapp.service.decrypt_secret", lambda _value: "token")
    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *_args, **_kwargs: {"data": [{"id": "catalog-connected"}]},
    )

    assert _catalog_link_warning(account=account, catalog_id="catalog-connected") is None


def test_meta_request_includes_error_data_details(monkeypatch):
    class FakeResponse:
        content = b'{"error":{"message":"(#131009) Parameter value is not valid"}}'
        status_code = 400
        text = (
            '{"error":{"message":"(#131009) Parameter value is not valid",'
            '"error_data":{"details":"product not found"}}}'
        )

        def json(self):
            return {
                "error": {
                    "message": "(#131009) Parameter value is not valid",
                    "error_data": {"details": "product not found"},
                }
            }

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def request(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.whatsapp.service.httpx.Client", FakeClient)

    with pytest.raises(HTTPException) as error:
        _meta_request("POST", "/api/v1/messages", access_token="token")

    assert error.value.detail == "(#131009) Parameter value is not valid: product not found"


def test_interactive_template_save_updates_existing_action_key(db):
    company, _ = bootstrap_company(db, "Acme")
    create_interactive_template(
        db,
        company_id=company.id,
        payload=AiInteractiveTemplateCreate(
            name="Menu principal",
            action_key="menu_principal",
            body_text="Selecciona una opcion",
            options=[AiInteractiveTemplateOption(id="menu_principal_opt_1", title="Cursos")],
        ),
    )

    updated = create_interactive_template(
        db,
        company_id=company.id,
        payload=AiInteractiveTemplateCreate(
            name="Menu actualizado",
            action_key=" MENU_PRINCIPAL ",
            body_text="Selecciona una opcion actualizada",
            options=[AiInteractiveTemplateOption(id="menu_principal_opt_1", title="Productos")],
        ),
    )
    rows = list_interactive_templates(db, company_id=company.id)

    assert len(rows) == 1
    assert rows[0].id == updated.id
    assert rows[0].name == "Menu actualizado"
    assert rows[0].options[0]["title"] == "Productos"


def test_ai_infers_menu_action_when_plain_reply_announces_configured_options():
    template = SimpleNamespace(
        action_key="menu_principal",
        name="Menu principal",
        body_text="Selecciona una de nuestras opciones",
        options=[
            {"id": "menu_principal_opt_1", "title": "Cursos"},
            {"id": "menu_principal_opt_2", "title": "Productos"},
            {"id": "menu_principal_opt_3", "title": "Agenda tu cita"},
        ],
    )

    action = _infer_interactive_action(
        reply_text=(
            "Gracias, Camilo. Ahora que tengo tus datos, aqui tienes las opciones "
            "que ofrecemos: cursos, productos y servicio de bronceado."
        ),
        agent_prompt=(
            "Despues de capturar nombre, email y ciudad, envia el menu principal "
            "de la biblioteca de interactivos."
        ),
        templates=[template],
    )

    assert action == "menu_principal"


def test_ai_does_not_infer_menu_action_for_unrelated_reply():
    template = SimpleNamespace(
        action_key="menu_principal",
        name="Menu principal",
        body_text="Selecciona una de nuestras opciones",
        options=[
            {"id": "menu_principal_opt_1", "title": "Cursos"},
            {"id": "menu_principal_opt_2", "title": "Productos"},
        ],
    )

    action = _infer_interactive_action(
        reply_text="Por favor comparteme tu correo para continuar.",
        agent_prompt="Envia el menu principal despues de capturar los datos.",
        templates=[template],
    )

    assert action is None


def test_interactive_after_capture_trigger_runs_once_per_conversation(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, phone="573000000000")
    account = WhatsAppAccount(
        company_id=company.id,
        phone_number_id="phone-id",
        business_account_id="waba-id",
        access_token_encrypted="not-used",
        verify_token="verify-token",
    )
    db.add_all([contact, account])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id)
    db.add(conversation)
    db.commit()

    create_interactive_template(
        db,
        company_id=company.id,
        payload=AiInteractiveTemplateCreate(
            name="Menu principal",
            action_key="menu_principal",
            body_text="Selecciona una opcion",
            options=[AiInteractiveTemplateOption(id="menu_principal_opt_1", title="Cursos")],
            usage_instruction="Enviar despues de capturar datos iniciales.",
            trigger_mode="after_capture",
            trigger_fields=["nombre", "email", "ciudad"],
        ),
    )

    action = _resolve_configured_action(
        db,
        account=account,
        conversation=conversation,
        contact=contact,
        ai_reply=AutoReplyResult(
            reply_text="Gracias, Camilo.",
            captured_fields={
                "nombre": "Camilo Sanchez",
                "correo": "cliente@example.com",
                "ciudad": "La Estrella",
            },
        ),
    )

    assert action == "menu_principal"
    assert contact.email == "cliente@example.com"
    assert contact.metadata_json["ai_captured_fields"]["ciudad"] == "La Estrella"

    db.add(
        Message(
            company_id=company.id,
            conversation_id=conversation.id,
            sender_type="agent",
            content="Selecciona una opcion",
            message_type="interactive",
            metadata_json={"source": "ai_action:menu_principal"},
        )
    )
    db.commit()

    repeated_action = _resolve_configured_action(
        db,
        account=account,
        conversation=conversation,
        contact=contact,
        ai_reply=AutoReplyResult(reply_text="Continuemos."),
    )

    assert repeated_action is None


def test_first_contact_does_not_skip_welcome_for_previously_captured_contact(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(
        company_id=company.id,
        phone="573000000000",
        metadata_json={
            "ai_captured_fields": {
                "nombre": "Camilo Sanchez",
                "email": "cliente@example.com",
                "ciudad": "La Estrella",
            }
        },
    )
    account = WhatsAppAccount(
        company_id=company.id,
        phone_number_id="phone-id",
        business_account_id="waba-id",
        access_token_encrypted="not-used",
        verify_token="verify-token",
    )
    db.add_all([contact, account])
    db.flush()
    conversation = Conversation(company_id=company.id, contact_id=contact.id)
    db.add(conversation)
    db.commit()

    create_interactive_template(
        db,
        company_id=company.id,
        payload=AiInteractiveTemplateCreate(
            name="Menu principal",
            action_key="menu_principal",
            body_text="Selecciona una opcion",
            options=[AiInteractiveTemplateOption(id="menu_principal_opt_1", title="Productos")],
            trigger_mode="after_capture",
            trigger_fields=["nombre", "email", "ciudad"],
        ),
    )

    action = _resolve_configured_action(
        db,
        account=account,
        conversation=conversation,
        contact=contact,
        ai_reply=AutoReplyResult(
            reply_text="Hola, soy Andrea.",
            is_first_contact=True,
        ),
    )

    assert action is None


def test_incoming_interactive_button_reply_exposes_visible_title_to_ai():
    content, reply = _incoming_message_content(
        {
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {
                    "id": "menu_principal_opt_3",
                    "title": "Agenda tu Cita",
                },
            },
        }
    )

    assert content == "Agenda tu Cita"
    assert reply == {
        "type": "button_reply",
        "id": "menu_principal_opt_3",
        "title": "Agenda tu Cita",
        "description": None,
    }
    assert _should_generate_auto_reply(
        message_type="interactive",
        content=content,
        conversation_status="open",
    )


def test_incoming_interactive_list_reply_keeps_option_metadata():
    content, reply = _incoming_message_content(
        {
            "type": "interactive",
            "interactive": {
                "type": "list_reply",
                "list_reply": {
                    "id": "servicios_opt_2",
                    "title": "Bronceado en camara",
                    "description": "Consulta planes disponibles",
                },
            },
        }
    )

    assert content == "Bronceado en camara"
    assert reply == {
        "type": "list_reply",
        "id": "servicios_opt_2",
        "title": "Bronceado en camara",
        "description": "Consulta planes disponibles",
    }


def test_selected_interactive_option_resolves_its_source_menu():
    template = SimpleNamespace(
        action_key="menu_principal",
        options=[
            {"id": "menu_principal_opt_1", "title": "Cursos"},
            {"id": "menu_principal_opt_2", "title": "Productos"},
            {"id": "menu_principal_opt_3", "title": "Agenda tu Cita"},
        ],
    )

    action_key = _selected_interactive_source_action(
        templates=[template],
        interactive_reply={
            "type": "button_reply",
            "id": "menu_principal_opt_2",
            "title": "Productos",
        },
    )

    assert action_key == "menu_principal"


def test_companies_routes_module_imports():
    from app.companies import routes

    assert routes.router.prefix == "/companies"

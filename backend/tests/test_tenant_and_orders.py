import json
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
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
from app.appointments.schemas import AppointmentCreate, AppointmentUpdate
from app.appointments.service import create_appointment, update_appointment
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
from app.ai.routes import get_default_system_prompt
from app.ai.models import AiAgent
from app.conversations.models import Conversation
from app.conversations.schemas import ConversationCreate
from app.conversations.service import (
    assign_conversation_funnel,
    assign_conversation,
    create_conversation,
    get_conversation,
    get_or_create_open_conversation,
    list_conversations,
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
from app.payments.notifications import notify_order_paid
from app.payments.service import process_payment_webhook
from app.orders.schemas import OrderCreate, OrderItemCreate
from app.orders.service import create_order, generate_payment_link, mark_paid_by_reference
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
from app.users.service import get_user
from app.whatsapp.models import WhatsAppAccount
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
    )
    contact = Contact(
        company_id=company.id,
        name="Cliente Uno",
        phone="+573001112233",
    )
    db.add_all([product, contact])
    db.commit()
    inventory = Inventory(
        company_id=company.id,
        product_id=product.id,
        quantity_available=10,
        quantity_reserved=0,
    )
    db.add(inventory)
    db.commit()

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            conversation_id=None,
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
    )
    db.add_all([contact, product])
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=5)
    db.add(inventory)
    db.commit()

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
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


def test_audit_logs_redact_integration_secrets(db):
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

    with pytest.raises(HTTPException) as exc_info:
        create_integration(
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
    assert exc_info.value.status_code == 422
    assert "Calendar provider is required" in str(exc_info.value.detail)

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
    assert len(requests) == 2
    assert requests[0]["method"] == "POST"
    assert requests[1]["method"] == "PATCH"

    synced_events = list(
        db.scalars(
            select(Event).where(
                Event.company_id == company.id,
                Event.event_type == "appointment.calendar_synced",
            )
        )
    )
    assert len(synced_events) == 2


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
            if len(calls) == 1:
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
    assert len(calls) == 2

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
    )
    db.add_all([contact, product])
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
    )
    db.add_all([contact_default, product_default])
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


def test_payment_webhook_idempotency_ignores_duplicate_transaction_ids(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Camiseta negra",
        sku="CAM-NEG",
        price=Decimal("80000.00"),
        currency="COP",
    )
    db.add_all([contact, product])
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


def test_mock_payment_webhook_ignores_duplicate_reference_without_transaction_id(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Gorra",
        sku="GOR-01",
        price=Decimal("35000.00"),
        currency="COP",
    )
    db.add_all([contact, product])
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=4)
    db.add(inventory)
    db.commit()

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
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


def test_payment_webhook_ignores_mismatched_provider_for_same_reference(db):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Demo", phone="573000000000")
    product = Product(
        company_id=company.id,
        name="Sudadera",
        sku="SUD-01",
        price=Decimal("95000.00"),
        currency="COP",
    )
    db.add_all([contact, product])
    db.flush()
    inventory = Inventory(company_id=company.id, product_id=product.id, quantity_available=2)
    db.add(inventory)
    db.commit()

    order = create_order(
        db,
        company_id=company.id,
        payload=OrderCreate(
            contact_id=contact.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1)],
        ),
    )
    order = generate_payment_link(db, company_id=company.id, order_id=order.id)

    payload = {
        "payment_reference": order.payment_reference,
        "status": "paid",
        "provider": "mercado_pago",
    }

    response = process_payment_webhook(db, provider="mercado_pago", payload=payload)
    assert response.status == "ignored"
    assert inventory.quantity_available == 2
    assert inventory.quantity_reserved == 1

    stored_order = db.scalar(select(Order).where(Order.id == order.id))
    assert stored_order is not None
    assert stored_order.status == "waiting_payment"


def test_inventory_listing_creates_missing_rows_for_tenant_products(db):
    company, _ = bootstrap_company(db, "Acme")
    product = Product(
        company_id=company.id,
        name="Bronceador profesional",
        sku="BRONCE-01",
        price=Decimal("130000.00"),
        currency="COP",
    )
    db.add(product)
    db.commit()

    rows = list_inventory(db, company_id=company.id, limit=50, offset=0)

    assert len(rows) == 1
    assert rows[0].product_id == product.id
    assert rows[0].quantity_available == 0
    assert rows[0].quantity_reserved == 0


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

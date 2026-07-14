from __future__ import annotations

import csv
import json
import io
import zipfile
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.auth.service import build_token
from app.audit.service import list_audit_logs, record_audit
from app.companies.schemas import CompanyCreate
from app.companies.service import create_company_with_owner
from app.ai.models import AiAgent, AiFaqEntry, AiInteractiveTemplate
from app.ai.schemas import AiAgentCreate, AiAgentUpdate
from app.ai import service as ai_service
from app.core.database import Base, get_db
from app.core.schemas import OwnerCreate
from app.core.security import hash_password
from app.funnels.models import SalesFunnel, SalesFunnelStep
from app.funnels.schemas import FunnelCreate, FunnelStepWrite, FunnelUpdate
from app.funnels import service as funnel_service
from app.appointments.schemas import AppointmentCreate
from app.appointments import service as appointment_service
from app.integrations.schemas import IntegrationCreate, OutboundWebhookCreate
from app.integrations.service import create_integration, create_outbound_webhook
from app.main import app
from app.contacts.models import Contact
from app.conversations.models import Conversation
from app.conversations import service as conversation_service
from app.events.models import Event
from app.inventory.models import Inventory
from app.messages.models import Message
from app.orders.models import Order, OrderItem
from app.products.models import Product
from app.appointments.models import Appointment
from app.whatsapp.models import WhatsAppAccount
from app.users.models import User


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


def auth_headers(user) -> dict[str, str]:
    return {"Authorization": f"Bearer {build_token(user)}"}


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db) -> TestClient:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_superadmin(db: Session, company_id):
    superadmin = User(
        company_id=company_id,
        name="Super Usuario",
        email="superadmin@swateck.com",
        password_hash=hash_password("super-secret"),
        role="superadmin",
    )
    db.add(superadmin)
    db.commit()
    return superadmin


def _prepare_export_dataset(
    db: Session, company_id, redaction_markers: dict[str, str] | None = None
):
    if redaction_markers is None:
        redaction_markers = {
            "integration_password": f"redaction-{company_id}-1",
            "integration_verify_token": f"redaction-{company_id}-2",
            "webhook_secret_token": f"redaction-{company_id}-3",
            "whatsapp_access_token": f"redaction-{company_id}-4",
            "whatsapp_verify_token": f"redaction-{company_id}-5",
            "audit_password_marker": f"redaction-{company_id}-6",
            "audit_secret_token_marker": f"redaction-{company_id}-7",
            "audit_verify_token_marker": f"redaction-{company_id}-8",
        }
    contact = Contact(
        company_id=company_id,
        name="Cliente Export",
        phone="573000000000",
        email="cliente@acme.com",
        source="whatsapp",
    )
    product = Product(
        company_id=company_id,
        name="Producto Export",
        sku="SKU-EXPORT",
        price=Decimal("125000.00"),
        currency="COP",
        status="active",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="retailer-1",
    )
    ai_agent = AiAgent(
        company_id=company_id,
        name="Asistente Export",
        system_prompt="Eres un asistente de ventas.",
        conversation_objective="Ayudar con ventas.",
        conversation_guide="Guia de conversacion.",
        security_rules="No inventar datos.",
        tone="amigable",
        rules={"operational": {"status": "draft", "version": 1, "draft": {"timezone": "UTC"}}},
        active=True,
    )
    ai_faq = AiFaqEntry(
        company_id=company_id,
        question="Horarios",
        answer="Atendemos de lunes a viernes.",
        active=True,
    )
    ai_template = AiInteractiveTemplate(
        company_id=company_id,
        name="Menu principal",
        action_key="main_menu",
        template_type="buttons",
        body_text="Elige una opcion",
        footer_text="Swaflow",
        button_text="Ver opciones",
        section_title="Opciones",
        options=[{"id": "sales", "title": "Ventas"}],
        usage_instruction="Mostrar al inicio.",
        trigger_mode="ai_decides",
        trigger_fields=["nombre"],
        active=True,
    )
    funnel = SalesFunnel(
        company_id=company_id,
        name="Funnel Export",
        system_key="export",
        description="Funnel de exportacion",
        status="active",
        is_default=False,
        welcome_message="Bienvenido",
        capture_fields=["Nombre", "Correo"],
        assignment_criteria="Solicitudes exportadas",
    )
    db.add_all([contact, product, ai_agent, ai_faq, ai_template, funnel])
    db.flush()

    funnel_step = SalesFunnelStep(
        company_id=company_id,
        funnel_id=funnel.id,
        position=1,
        name="Paso 1",
        code="paso_1",
        prompt="Saluda",
        objectives=["saludar"],
        transition_criteria="Respuesta recibida",
        status="active",
        config={"entry_point": True},
    )
    whatsapp_account = WhatsAppAccount(
        company_id=company_id,
        phone_number_id="phone-1",
        business_account_id="business-1",
        access_token_encrypted=redaction_markers["whatsapp_access_token"],
        verify_token=redaction_markers["whatsapp_verify_token"],
        status="active",
    )
    db.add_all([funnel_step, whatsapp_account])
    db.flush()

    conversation = Conversation(
        company_id=company_id,
        contact_id=contact.id,
        channel="whatsapp",
        status="open",
        unread_count=2,
    )
    db.add(conversation)
    db.flush()

    message = Message(
        company_id=company_id,
        conversation_id=conversation.id,
        external_message_id="wamid.export.1",
        sender_type="customer",
        content="Quiero comprar",
        message_type="text",
        metadata_json={"channel": "whatsapp"},
    )
    inventory = Inventory(
        company_id=company_id,
        product_id=product.id,
        quantity_available=7,
        quantity_reserved=2,
    )
    order = Order(
        company_id=company_id,
        contact_id=contact.id,
        conversation_id=conversation.id,
        status="waiting_payment",
        total=Decimal("125000.00"),
        currency="COP",
        payment_provider="wompi",
        payment_reference="ref-export-1",
        payment_status="pending",
        metadata_json={"channel": "whatsapp"},
    )
    db.add_all([message, inventory, order])
    db.flush()

    order_item = OrderItem(
        company_id=company_id,
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=Decimal("125000.00"),
        total=Decimal("125000.00"),
    )
    appointment = Appointment(
        company_id=company_id,
        contact_id=contact.id,
        conversation_id=conversation.id,
        assigned_user_id=None,
        scheduled_at=datetime(2026, 6, 30, 15, tzinfo=UTC),
        duration_minutes=60,
        status="scheduled",
        notes="Cita comercial",
        external_calendar_event_id="calendar-event-1",
        calendar_sync_status="synced",
        calendar_synced_at=datetime(2026, 6, 29, 15, tzinfo=UTC),
    )
    integration = create_integration(
        db,
        company_id=company_id,
        payload=IntegrationCreate(
            type="email",
            credentials=json.dumps(
                {"smtp_password": redaction_markers["integration_password"]}
            ),
            config={
                "provider": "smtp",
                "from_email": "notificaciones@acme.com",
                "smtp_host": "smtp.acme.com",
                "smtp_port": "587",
                "smtp_user": "mailer",
                "verify_token": redaction_markers["integration_verify_token"],
            },
        ),
    )
    webhook = create_outbound_webhook(
        db,
        company_id=company_id,
        payload=OutboundWebhookCreate(
            event_type="order.paid",
            target_url="https://example.com/hooks/orders",
            secret_token=redaction_markers["webhook_secret_token"],
            active=True,
        ),
    )
    event = Event(
        company_id=company_id,
        event_type="order.paid",
        payload={"order_id": str(order.id), "amount": "125000.00"},
        status="processed",
        processed_at=datetime(2026, 6, 29, 15, tzinfo=UTC),
    )
    db.add_all([order_item, appointment, event])
    db.flush()

    record_audit(
        db,
        company_id=company_id,
        actor_user=None,
        action="integration.updated",
        entity_type="integration",
        entity_id=integration.id,
        summary="Integration updated",
        metadata={
            "credentials": {
                "password": redaction_markers["audit_password_marker"]
            },
            "secret_token": redaction_markers["audit_secret_token_marker"],
            "nested": {"verify_token": redaction_markers["audit_verify_token_marker"]},
        },
    )
    record_audit(
        db,
        company_id=company_id,
        actor_user=None,
        action="outbound_webhook.updated",
        entity_type="outbound_webhook",
        entity_id=webhook.id,
        summary="Webhook updated",
        metadata={"secret_token": redaction_markers["audit_secret_token_marker"]},
    )
    db.commit()
    return {
        "contact": contact,
        "product": product,
        "conversation": conversation,
        "message": message,
        "inventory": inventory,
        "order": order,
        "appointment": appointment,
        "integration": integration,
        "webhook": webhook,
        "event": event,
    }


def test_superadmin_cross_tenant_access_is_audited(db, client):
    target_company, owner = bootstrap_company(db, "Acme")
    swateck_company, _ = bootstrap_company(db, "Swateck")
    superadmin = _create_superadmin(db, swateck_company.id)

    company_response = client.get(
        f"/api/v1/companies/{target_company.id}",
        headers=auth_headers(superadmin),
    )
    assert company_response.status_code == 200
    assert company_response.json()["name"] == "Acme"

    user_response = client.get(
        f"/api/v1/users/{owner.id}",
        headers=auth_headers(superadmin),
    )
    assert user_response.status_code == 200
    assert user_response.json()["email"] == owner.email

    company_access_log = next(
        log
        for log in list_audit_logs(db, company_id=target_company.id, limit=20, offset=0)
        if log.action == "superadmin.access_company"
    )
    assert company_access_log.actor_user_id == superadmin.id
    assert company_access_log.actor_role == "superadmin"
    assert company_access_log.metadata_json["access_scope"] == "cross_tenant"

    user_access_log = next(
        log
        for log in list_audit_logs(db, company_id=target_company.id, limit=20, offset=0)
        if log.action == "superadmin.access_user"
    )
    assert user_access_log.actor_user_id == superadmin.id
    assert user_access_log.metadata_json["access_scope"] == "cross_tenant"


def test_superadmin_offboarding_export_survives_audit_failure(db, client, monkeypatch):
    target_company, owner = bootstrap_company(db, "Acme")
    swateck_company, _ = bootstrap_company(db, "Swateck")
    superadmin = _create_superadmin(db, swateck_company.id)
    redaction_markers = {
        "integration_password": f"redaction-{target_company.id}-1",
        "integration_verify_token": f"redaction-{target_company.id}-2",
        "webhook_secret_token": f"redaction-{target_company.id}-3",
        "whatsapp_access_token": f"redaction-{target_company.id}-4",
        "whatsapp_verify_token": f"redaction-{target_company.id}-5",
        "audit_password_marker": f"redaction-{target_company.id}-6",
        "audit_secret_token_marker": f"redaction-{target_company.id}-7",
        "audit_verify_token_marker": f"redaction-{target_company.id}-8",
    }
    _prepare_export_dataset(db, target_company.id, redaction_markers)

    audit_calls = {"count": 0}

    def boom(*args, **kwargs):
        audit_calls["count"] += 1
        raise RuntimeError("audit failed")

    monkeypatch.setattr("app.offboarding.service.record_audit", boom)

    response = client.get(
        f"/api/v1/offboarding/export/{target_company.id}",
        headers=auth_headers(superadmin),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert str(target_company.id) in response.headers["content-disposition"]
    assert audit_calls["count"] >= 1

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    expected_headers = {
        "company.txt": [
            "id",
            "name",
            "status",
            "contact_email",
            "contact_phone",
            "currency",
            "timezone",
            "business_mode",
            "logo_url",
            "banner_url",
            "profile_url",
            "created_at",
            "updated_at",
        ],
        "users.txt": ["id", "name", "email", "role", "status", "module_permissions_json", "created_at", "updated_at"],
        "contacts.txt": ["id", "name", "phone", "email", "source", "status", "metadata_json", "created_at", "updated_at"],
        "conversations.txt": [
            "id",
            "contact_id",
            "channel",
            "status",
            "assigned_user_id",
            "funnel_id",
            "funnel_step_id",
            "current_step",
            "last_message_at",
            "unread_count",
            "created_at",
            "updated_at",
        ],
        "messages.txt": [
            "id",
            "conversation_id",
            "external_message_id",
            "sender_type",
            "message_type",
            "content",
            "metadata_json",
            "created_at",
        ],
        "products.txt": [
            "id",
            "name",
            "description",
            "sku",
            "price",
            "currency",
            "status",
            "whatsapp_catalog_id",
            "whatsapp_product_retailer_id",
            "metadata_json",
            "created_at",
            "updated_at",
        ],
        "ai_agents.txt": [
            "id",
            "name",
            "system_prompt",
            "conversation_objective",
            "conversation_guide",
            "security_rules",
            "tone",
            "rules_json",
            "active",
            "created_at",
            "updated_at",
        ],
        "ai_faq_entries.txt": ["id", "question", "answer", "active", "created_at", "updated_at"],
        "ai_interactive_templates.txt": [
            "id",
            "name",
            "action_key",
            "template_type",
            "body_text",
            "footer_text",
            "button_text",
            "section_title",
            "options_json",
            "usage_instruction",
            "trigger_mode",
            "trigger_fields_json",
            "active",
            "created_at",
            "updated_at",
        ],
        "sales_funnels.txt": [
            "id",
            "name",
            "system_key",
            "description",
            "status",
            "is_default",
            "welcome_message",
            "capture_fields_json",
            "assignment_criteria",
            "created_at",
            "updated_at",
        ],
        "sales_funnel_steps.txt": [
            "id",
            "funnel_id",
            "position",
            "name",
            "code",
            "prompt",
            "objectives_json",
            "transition_criteria",
            "status",
            "config_json",
            "created_at",
            "updated_at",
        ],
        "whatsapp_accounts.txt": [
            "id",
            "phone_number_id",
            "business_account_id",
            "status",
            "access_token_configured",
            "verify_token_configured",
            "created_at",
            "updated_at",
        ],
        "inventory.txt": ["id", "product_id", "quantity_available", "quantity_reserved", "updated_at"],
        "orders.txt": [
            "id",
            "contact_id",
            "conversation_id",
            "status",
            "total",
            "currency",
            "payment_provider",
            "payment_reference",
            "payment_status",
            "metadata_json",
            "created_at",
            "updated_at",
        ],
        "order_items.txt": ["id", "order_id", "product_id", "quantity", "unit_price", "total", "created_at"],
        "appointments.txt": [
            "id",
            "contact_id",
            "conversation_id",
            "assigned_user_id",
            "scheduled_at",
            "duration_minutes",
            "status",
            "notes",
            "external_calendar_event_id",
            "calendar_sync_status",
            "calendar_synced_at",
            "calendar_sync_obsolete_at",
            "created_at",
            "updated_at",
        ],
        "events.txt": ["id", "event_type", "status", "processed_at", "payload_json", "created_at"],
        "audit_logs.txt": [
            "id",
            "actor_user_id",
            "actor_role",
            "action",
            "entity_type",
            "entity_id",
            "summary",
            "metadata_json",
            "created_at",
        ],
        "integrations.txt": ["id", "type", "status", "credentials_configured", "config_json", "created_at", "updated_at"],
        "outbound_webhooks.txt": ["id", "event_type", "target_url", "active", "secret_configured", "created_at", "updated_at"],
    }
    expected = {
        "company.txt",
        "users.txt",
        "contacts.txt",
        "conversations.txt",
        "messages.txt",
        "products.txt",
        "ai_agents.txt",
        "ai_faq_entries.txt",
        "ai_interactive_templates.txt",
        "sales_funnels.txt",
        "sales_funnel_steps.txt",
        "whatsapp_accounts.txt",
        "inventory.txt",
        "orders.txt",
        "order_items.txt",
        "appointments.txt",
        "events.txt",
        "audit_logs.txt",
        "integrations.txt",
        "outbound_webhooks.txt",
    }
    assert expected.issubset(set(names))

    for name in expected:
        content = archive.read(name).decode("utf-8")
        rows = list(csv.reader(io.StringIO(content), delimiter="|"))
        assert rows, name
        assert len(rows) >= 2, name
        assert rows[0] == expected_headers[name], name
        for row in rows[1:]:
            assert len(row) == len(rows[0]), name
        assert str(swateck_company.id) not in content, name

    assert "Cliente Export" in archive.read("contacts.txt").decode("utf-8")
    assert "Producto Export" in archive.read("products.txt").decode("utf-8")
    assert "Asistente Export" in archive.read("ai_agents.txt").decode("utf-8")
    assert "Swateck" not in archive.read("contacts.txt").decode("utf-8")
    assert "Swateck" not in archive.read("products.txt").decode("utf-8")
    assert "Swateck" not in archive.read("ai_agents.txt").decode("utf-8")

    company_text = archive.read("company.txt").decode("utf-8")
    assert "Acme" in company_text
    assert str(target_company.id) in company_text
    assert "Swateck" not in company_text

    for name in expected:
        content = archive.read(name).decode("utf-8")
        for marker in redaction_markers.values():
            assert marker not in content, name

    users_text = archive.read("users.txt").decode("utf-8")
    assert owner.name in users_text
    assert owner.email in users_text
    assert "superadmin@swateck.com" not in users_text


def test_sensitive_writes_are_audited(db):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(
        company_id=company.id,
        name="Cliente Chat",
        phone="573111111111",
        email="chat@acme.com",
        source="whatsapp",
    )
    db.add(contact)
    db.flush()
    conversation = Conversation(
        company_id=company.id,
        contact_id=contact.id,
        channel="whatsapp",
        status="open",
    )
    db.add(conversation)
    db.flush()

    agent_user = User(
        company_id=company.id,
        name="Agente",
        email="agent@acme.example.com",
        password_hash=hash_password("super-secret"),
        role="agent",
    )
    db.add(agent_user)
    db.commit()
    db.refresh(agent_user)

    ai_agent = ai_service.create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="AI Acme",
            system_prompt="Ayuda a vender.",
            active=True,
        ),
        actor_user=owner,
    )
    ai_service.update_agent(
        db,
        company_id=company.id,
        agent_id=ai_agent.id,
        payload=AiAgentUpdate(active=False),
        actor_user=owner,
    )

    funnel = funnel_service.create_funnel(
        db,
        company_id=company.id,
        payload=FunnelCreate(name="Funnel Chat", steps=[]),
        actor_user=owner,
    )
    funnel_service.update_funnel(
        db,
        company_id=company.id,
        funnel_id=funnel.id,
        payload=FunnelUpdate(description="Funnel actualizado"),
        actor_user=owner,
    )

    appointment = appointment_service.create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            conversation_id=conversation.id,
            scheduled_at=datetime(2026, 6, 30, 15, tzinfo=UTC),
            duration_minutes=30,
            notes="Reunion comercial",
        ),
        actor_user=owner,
    )
    appointment_service.cancel_appointment(
        db,
        company_id=company.id,
        appointment_id=appointment.id,
        actor_user=owner,
    )

    reassigned = conversation_service.assign_conversation(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        assigned_user_id=agent_user.id,
        actor_user=owner,
    )
    assert reassigned.assigned_user_id == agent_user.id

    message = conversation_service.append_message(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        sender_type="agent",
        content="Hola, ya te atiendo.",
        actor_user=owner,
    )
    assert message.content == "Hola, ya te atiendo."

    audit_actions = {log.action for log in list_audit_logs(db, company_id=company.id, limit=50, offset=0)}
    assert "ai.agent.updated" in audit_actions
    assert "funnel.updated" in audit_actions
    assert "appointment.cancelled" in audit_actions
    assert "conversation.assigned" in audit_actions
    assert "message.created" in audit_actions


def test_superadmin_export_pack_includes_module_files_and_redacts_secrets(db, client):
    company, _ = bootstrap_company(db, "Acme")
    swateck_company, _ = bootstrap_company(db, "Swateck")
    superadmin = _create_superadmin(db, swateck_company.id)
    _prepare_export_dataset(db, company.id)

    response = client.get(
        f"/api/v1/offboarding/export/{company.id}",
        headers=auth_headers(superadmin),
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert str(company.id) in response.headers["content-disposition"]

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    expected = {
        "company.txt",
        "users.txt",
        "contacts.txt",
        "conversations.txt",
        "messages.txt",
        "products.txt",
        "ai_agents.txt",
        "ai_faq_entries.txt",
        "ai_interactive_templates.txt",
        "sales_funnels.txt",
        "sales_funnel_steps.txt",
        "whatsapp_accounts.txt",
        "inventory.txt",
        "orders.txt",
        "order_items.txt",
        "appointments.txt",
        "events.txt",
        "audit_logs.txt",
        "integrations.txt",
        "outbound_webhooks.txt",
    }
    assert expected.issubset(names)

    archive_text = "\n".join(archive.read(name).decode("utf-8") for name in expected)
    assert "smtp-secret" not in archive_text
    assert "webhook-secret" not in archive_text
    assert "verify-secret" not in archive_text
    assert "smtp_password" not in archive_text
    assert "encrypted-access-token" not in archive_text
    assert "verify-secret-token" not in archive_text

    company_text = archive.read("company.txt").decode("utf-8")
    assert "Acme" in company_text
    assert "logo_url" in company_text

    ai_agent_text = archive.read("ai_agents.txt").decode("utf-8")
    assert "Asistente Export" in ai_agent_text
    assert "rules_json" in ai_agent_text

    funnels_text = archive.read("sales_funnels.txt").decode("utf-8")
    assert "Funnel Export" in funnels_text

    whatsapp_text = archive.read("whatsapp_accounts.txt").decode("utf-8")
    assert "access_token_configured" in whatsapp_text
    assert "verify_token_configured" in whatsapp_text
    assert "encrypted-access-token" not in whatsapp_text

    integration_text = archive.read("integrations.txt").decode("utf-8")
    assert "credentials_configured" in integration_text
    assert "verify_token" not in integration_text

    webhook_text = archive.read("outbound_webhooks.txt").decode("utf-8")
    assert "secret_configured" in webhook_text
    assert "webhook-secret" not in webhook_text

    export_log = next(
        log
        for log in list_audit_logs(db, company_id=company.id, limit=20, offset=0)
        if log.action == "tenant.export_created"
    )
    assert export_log.actor_user_id == superadmin.id
    assert export_log.metadata_json["filename"].endswith(".zip")
    assert export_log.metadata_json["module_count"] >= 16


def test_non_superadmin_cannot_export_another_tenant(db, client):
    _company, _ = bootstrap_company(db, "Acme")
    other_company, owner = bootstrap_company(db, "Beta")

    response = client.get(
        f"/api/v1/offboarding/export/{other_company.id}",
        headers=auth_headers(owner),
    )
    assert response.status_code == 403

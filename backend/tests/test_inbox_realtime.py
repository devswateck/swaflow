from collections.abc import Generator
from decimal import Decimal
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from app import models  # noqa: F401
from app.auth.service import build_token
from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentCreate
from app.appointments.schemas import AppointmentUpdate
from app.appointments.service import create_appointment
from app.appointments.service import update_appointment
from app.ai.schemas import AiAgentCreate
from app.ai.service import create_agent
from app.companies.schemas import CompanyCreate
from app.companies.service import create_company_with_owner
from app.core.database import Base, get_db
from app.core.schemas import OwnerCreate
from app.conversations.schemas import ConversationCreate
from app.conversations.service import (
    append_message,
    assign_conversation,
    assign_conversation_funnel,
    close_conversation,
    create_conversation,
    mark_conversation_read,
    set_conversation_ai_enabled,
)
from app.conversations.models import Conversation
from app.contacts.models import Contact
from app.events.service import list_conversation_events
from app.events.service import create_event
from app.main import app
from app.messages.models import Message
from app.orders.schemas import OrderCreate, OrderItemCreate
from app.orders.service import create_order
from app.products.models import Product
from app.inventory.models import Inventory
from app.realtime import _authenticate_socket
from app.users.schemas import UserCreate
from app.users.service import create_user
from app.whatsapp.schemas import WhatsAppAccountCreate
from app.whatsapp.service import create_account
from app.whatsapp.service import process_webhook_payload


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


@pytest.fixture()
def db() -> Generator[Session, None, None]:
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
def client(db) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_headers(user) -> dict[str, str]:
    return {"Authorization": f"Bearer {build_token(user)}"}


def test_inbox_detail_includes_events_and_orders_by_recent_activity(db, client):
    company, owner = bootstrap_company(db, "Acme")
    other_company, other_owner = bootstrap_company(db, "Bravo")

    first_contact = Contact(company_id=company.id, name="Cliente 1", phone="+573001112233")
    second_contact = Contact(company_id=company.id, name="Cliente 2", phone="+573001112234")
    other_contact = Contact(company_id=other_company.id, name="Cliente 3", phone="+573001112235")
    db.add_all([first_contact, second_contact, other_contact])
    db.commit()

    first_conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=first_contact.id, channel="whatsapp"),
    )
    second_conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=second_contact.id, channel="whatsapp"),
    )
    other_conversation = create_conversation(
        db,
        company_id=other_company.id,
        payload=ConversationCreate(contact_id=other_contact.id, channel="whatsapp"),
    )

    append_message(
        db,
        company_id=company.id,
        conversation_id=first_conversation.id,
        sender_type="customer",
        content="Hola, quiero saber mas",
        external_message_id="wamid-1",
    )
    append_message(
        db,
        company_id=company.id,
        conversation_id=second_conversation.id,
        sender_type="agent",
        content="Claro, te ayudo",
        external_message_id="wamid-2",
    )
    append_message(
        db,
        company_id=other_company.id,
        conversation_id=other_conversation.id,
        sender_type="customer",
        content="Mensaje ajeno",
        external_message_id="wamid-3",
    )

    first_conversation.last_message_at = datetime.now(UTC) - timedelta(hours=2)
    first_conversation.unread_count = 2
    second_conversation.last_message_at = datetime.now(UTC)
    second_conversation.unread_count = 1
    other_conversation.last_message_at = datetime.now(UTC) - timedelta(minutes=30)
    db.flush()

    create_event(
        db,
        company_id=company.id,
        event_type="message.received",
        payload={
            "conversation_id": str(second_conversation.id),
            "message_id": "wamid-2",
        },
    )
    create_event(
        db,
        company_id=company.id,
        event_type="message.status",
        payload={
            "conversation_id": str(second_conversation.id),
            "message_id": "wamid-2",
            "status": "delivered",
        },
    )
    product = Product(
        company_id=company.id,
        name="Producto contexto",
        price=Decimal("12000"),
        currency="COP",
        status="active",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="producto-contexto",
    )
    db.add(product)
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=product.id,
            quantity_available=5,
            quantity_reserved=0,
        )
    )
    db.commit()

    published: list[tuple[str, dict]] = []

    def capture_publish(company_id, event_type, payload):
        published.append((event_type, payload))

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "app.appointments.service.sync_appointment_with_calendar",
        lambda *args, **kwargs: SimpleNamespace(
            external_event_id="calendar-1",
            raw={"provider": "mock"},
        ),
    )
    monkeypatch.setattr("app.appointments.service.realtime_manager.publish", capture_publish)
    monkeypatch.setattr("app.orders.service.realtime_manager.publish", capture_publish)
    monkeypatch.setattr("app.conversations.service.realtime_manager.publish", capture_publish)
    monkeypatch.setattr("app.whatsapp.service.realtime_manager.publish", capture_publish)
    try:
        appointment_time = datetime(2026, 6, 30, 10, 0, tzinfo=UTC)
        create_appointment(
            db,
            company_id=company.id,
            payload=AppointmentCreate(
                contact_id=second_contact.id,
                conversation_id=second_conversation.id,
                scheduled_at=appointment_time,
                duration_minutes=45,
                notes="Seguimiento",
            ),
        )
        create_order(
            db,
            company_id=company.id,
            payload=OrderCreate(
                contact_id=second_contact.id,
                conversation_id=second_conversation.id,
                items=[OrderItemCreate(product_id=product.id, quantity=1)],
                metadata={},
            ),
        )
        assign_conversation(
            db,
            company_id=company.id,
            conversation_id=second_conversation.id,
            assigned_user_id=owner.id,
        )
        assign_conversation_funnel(
            db,
            company_id=company.id,
            conversation_id=second_conversation.id,
            funnel_id=None,
            funnel_step_id=None,
            current_step="seguimiento",
        )
        close_conversation(
            db,
            company_id=company.id,
            conversation_id=second_conversation.id,
        )
    finally:
        monkeypatch.undo()
    db.commit()

    published_types = [event_type for event_type, _ in published]
    assert "appointment.created" in published_types
    assert "appointment.calendar_synced" in published_types
    assert "order.created" in published_types
    assert "conversation.assigned" in published_types
    assert "conversation.funnel_assigned" in published_types
    assert "conversation.closed" in published_types
    assert all(
        payload.get("conversation_id") == str(second_conversation.id)
        for event_type, payload in published
        if event_type in {
            "appointment.created",
            "appointment.calendar_synced",
            "order.created",
            "conversation.assigned",
            "conversation.funnel_assigned",
            "conversation.closed",
        }
    )

    inbox_response = client.get("/api/v1/conversations", headers=auth_headers(owner))
    assert inbox_response.status_code == 200
    inbox_rows = inbox_response.json()
    assert [row["id"] for row in inbox_rows] == [str(second_conversation.id), str(first_conversation.id)]
    assert inbox_rows[0]["last_message"] == "Claro, te ayudo"
    assert inbox_rows[0]["unread_count"] == 1
    assert inbox_rows[0]["available_product_count"] == 1
    assert inbox_rows[1]["last_message"] == "Hola, quiero saber mas"

    detail_response = client.get(
        f"/api/v1/conversations/{second_conversation.id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == str(second_conversation.id)
    assert detail["available_product_count"] == 1
    assert detail["available_products_preview"][0]["name"] == "Producto contexto"
    assert detail["available_products_preview"][0]["available_units"] == 4
    event_types = [event["event_type"] for event in detail["events"]]
    assert set(event_types) == {
        "appointment.calendar_synced",
        "appointment.created",
        "conversation.assigned",
        "conversation.closed",
        "conversation.funnel_assigned",
        "message.received",
        "message.status",
        "order.created",
    }
    assert all(
        event["payload"]["conversation_id"] == str(second_conversation.id)
        for event in detail["events"]
    )

    cross_tenant_response = client.get(
        f"/api/v1/conversations/{second_conversation.id}",
        headers=auth_headers(other_owner),
    )
    assert cross_tenant_response.status_code == 404


def test_inbox_detail_counts_only_meta_synced_available_products(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente 1", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    synced_product = Product(
        company_id=company.id,
        name="Producto contexto",
        price=Decimal("12000"),
        currency="COP",
        status="active",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="producto-contexto",
    )
    local_product = Product(
        company_id=company.id,
        name="Producto local",
        price=Decimal("15000"),
        currency="COP",
        status="active",
    )
    db.add_all([synced_product, local_product])
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=synced_product.id,
            quantity_available=5,
            quantity_reserved=1,
        )
    )
    db.add(
        Inventory(
            company_id=company.id,
            product_id=local_product.id,
            quantity_available=7,
            quantity_reserved=0,
        )
    )
    db.commit()

    response = client.get(f"/api/v1/conversations/{conversation.id}", headers=auth_headers(owner))

    assert response.status_code == 200
    detail = response.json()
    assert detail["available_product_count"] == 1
    assert [item["name"] for item in detail["available_products_preview"]] == ["Producto contexto"]
    assert detail["available_products_preview"][0]["available_units"] == 4


def test_manual_whatsapp_send_persists_history_and_realtime_event(db, client, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")
    account = create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-1",
            business_account_id="waba-1",
            access_token="token-1",
            verify_token="verify-1",
        ),
    )

    published: list[tuple[str, dict]] = []

    def capture_publish(company_id, event_type, payload):
        published.append((event_type, payload))

    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-manual-1"}]},
    )
    monkeypatch.setattr("app.whatsapp.service.realtime_manager.publish", capture_publish)

    response = client.post(
        "/api/v1/whatsapp/messages",
        headers=auth_headers(owner),
        json={
            "to": "+573001112233",
            "body": "Hola, te escribo por el pedido",
            "account_id": str(account.id),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["meta_message_id"] == "wamid-manual-1"

    conversation_id = payload["conversation_id"]
    message_id = payload["message_id"]
    stored_message = db.scalar(select(Message).where(Message.id == UUID(message_id)))
    assert stored_message is not None
    assert stored_message.company_id == company.id
    assert stored_message.sender_type == "agent"
    assert stored_message.message_type == "text"
    assert stored_message.content == "Hola, te escribo por el pedido"
    assert stored_message.metadata_json["source"] == "agent_manual"

    detail_response = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert [message["content"] for message in detail["messages"]] == [
        "Hola, te escribo por el pedido"
    ]
    assert "message.sent" in [event["event_type"] for event in detail["events"]]
    assert published[0][0] == "message.sent"
    assert published[0][1]["conversation_id"] == conversation_id
    assert published[0][1]["message_id"] == message_id


def test_conversation_send_message_only_appends_local_history(db, client, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    conversation_id = conversation.id

    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("No debe llamar WhatsApp")),
    )

    response = client.post(
        f"/api/v1/conversations/{conversation.id}/send-message",
        headers=auth_headers(owner),
        json={"content": "Respuesta manual solo local"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sender_type"] == "agent"
    assert payload["content"] == "Respuesta manual solo local"
    assert payload["message_type"] == "text"

    detail_response = client.get(
        f"/api/v1/conversations/{conversation.id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert [message["content"] for message in detail["messages"]] == [
        "Respuesta manual solo local"
    ]
    assert "message.sent" not in [event["event_type"] for event in detail["events"]]


def test_incoming_interactive_reply_preserves_metadata_in_history(db, client, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")
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
    monkeypatch.setattr("app.whatsapp.service.generate_auto_reply", lambda *args, **kwargs: None)

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-1"},
                                "contacts": [
                                    {
                                        "wa_id": "573001112233",
                                        "profile": {"name": "Cliente"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "wamid-interactive-1",
                                        "from": "573001112233",
                                        "timestamp": "1710000000",
                                        "type": "interactive",
                                        "interactive": {
                                            "type": "button_reply",
                                            "button_reply": {
                                                "id": "menu_principal_opt_2",
                                                "title": "Agenda tu cita",
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

    message = db.scalar(
        select(Message).where(Message.external_message_id == "wamid-interactive-1")
    )
    assert message is not None
    assert message.company_id == company.id
    assert message.sender_type == "customer"
    assert message.message_type == "interactive"
    assert message.content == "Agenda tu cita"
    assert message.metadata_json["interactive_reply"] == {
        "type": "button_reply",
        "id": "menu_principal_opt_2",
        "title": "Agenda tu cita",
        "description": None,
    }

    detail_response = client.get(
        f"/api/v1/conversations/{message.conversation_id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["messages"][0]["content"] == "Agenda tu cita"
    assert detail["messages"][0]["message_type"] == "interactive"
    assert "message.received" in [event["event_type"] for event in detail["events"]]


def test_inbox_keeps_recency_after_state_only_change(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact_a = Contact(company_id=company.id, name="Cliente A", phone="+573001112233")
    contact_b = Contact(company_id=company.id, name="Cliente B", phone="+573001112234")
    db.add_all([contact_a, contact_b])
    db.commit()

    recent_conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact_a.id, channel="whatsapp"),
    )
    stale_conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact_b.id, channel="whatsapp"),
    )

    append_message(
        db,
        company_id=company.id,
        conversation_id=recent_conversation.id,
        sender_type="customer",
        content="Mensaje reciente",
        external_message_id="wamid-recent",
    )
    append_message(
        db,
        company_id=company.id,
        conversation_id=stale_conversation.id,
        sender_type="customer",
        content="Mensaje viejo",
        external_message_id="wamid-old",
    )
    recent_conversation.last_message_at = datetime.now(UTC)
    stale_conversation.last_message_at = datetime.now(UTC) - timedelta(hours=2)
    db.commit()

    assign_conversation(
        db,
        company_id=company.id,
        conversation_id=stale_conversation.id,
        assigned_user_id=owner.id,
    )
    db.commit()

    inbox_response = client.get("/api/v1/conversations", headers=auth_headers(owner))
    assert inbox_response.status_code == 200
    inbox_rows = inbox_response.json()
    assert [row["id"] for row in inbox_rows[:2]] == [
        str(recent_conversation.id),
        str(stale_conversation.id),
    ]


def test_list_conversation_events_paginates_status_events_after_merge(db):
    company, _owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    message = append_message(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        sender_type="agent",
        content="Mensaje enviado",
        external_message_id="wamid-pagination",
    )

    first_event = create_event(
        db,
        company_id=company.id,
        event_type="message.received",
        payload={"conversation_id": str(conversation.id), "message_id": "wamid-first"},
    )
    status_event = create_event(
        db,
        company_id=company.id,
        event_type="message.status",
        payload={"message_id": message.external_message_id, "status": "delivered"},
    )
    last_event = create_event(
        db,
        company_id=company.id,
        event_type="message.received",
        payload={"conversation_id": str(conversation.id), "message_id": "wamid-last"},
    )

    first_event.created_at = datetime.now(UTC) - timedelta(minutes=3)
    status_event.created_at = datetime.now(UTC) - timedelta(minutes=2)
    last_event.created_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    page = list_conversation_events(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        limit=1,
        offset=1,
    )

    assert [event.id for event in page] == [status_event.id]


def test_list_conversation_events_applies_limit_and_offset_without_status_events(db):
    company, _owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )

    first_event = create_event(
        db,
        company_id=company.id,
        event_type="message.received",
        payload={"conversation_id": str(conversation.id), "message_id": "wamid-1"},
    )
    second_event = create_event(
        db,
        company_id=company.id,
        event_type="conversation.read",
        payload={"conversation_id": str(conversation.id), "unread_count": 0},
    )
    third_event = create_event(
        db,
        company_id=company.id,
        event_type="conversation.closed",
        payload={"conversation_id": str(conversation.id), "status": "closed"},
    )
    first_event.created_at = datetime.now(UTC) - timedelta(minutes=3)
    second_event.created_at = datetime.now(UTC) - timedelta(minutes=2)
    third_event.created_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    page = list_conversation_events(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        limit=1,
        offset=1,
    )

    assert [event.id for event in page] == [second_event.id]


def test_conversation_timeline_does_not_truncate_after_one_hundred_events(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )

    for index in range(105):
        create_event(
            db,
            company_id=company.id,
            event_type="message.status",
            payload={
                "conversation_id": str(conversation.id),
                "message_id": f"wamid-{index}",
                "status": "delivered",
            },
        )
    db.commit()

    response = client.get(f"/api/v1/conversations/{conversation.id}", headers=auth_headers(owner))
    assert response.status_code == 200
    detail = response.json()
    assert len(detail["events"]) == 105


def test_realtime_broadcasts_updates_and_rejects_invalid_token(db, client, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
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
    append_message(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        sender_type="customer",
        content="Hola",
        external_message_id="wamid-99",
    )
    db.commit()

    assert _authenticate_socket("invalid-token") is None

    published: list[tuple[str, dict]] = []

    def capture_publish(company_id, event_type, payload):
        published.append((event_type, payload))

    monkeypatch.setattr("app.conversations.service.realtime_manager.publish", capture_publish)
    monkeypatch.setattr("app.whatsapp.service.realtime_manager.publish", capture_publish)

    mark_conversation_read(db, company_id=company.id, conversation_id=conversation.id)
    assert published[0][0] == "conversation.read"
    assert published[0][1]["conversation_id"] == str(conversation.id)
    assert published[0][1]["unread_count"] == 0

    detail_response = client.get(
        f"/api/v1/conversations/{conversation.id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert "conversation.read" in [event["event_type"] for event in detail["events"]]

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-1"},
                                "statuses": [
                                    {
                                        "id": "wamid-99",
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

    assert published[1][0] == "message.status"
    assert published[1][1]["conversation_id"] == str(conversation.id)
    assert published[1][1]["message_id"] == "wamid-99"
    assert published[1][1]["status"] == "delivered"


def test_ai_pause_and_resume_controls_auto_reply_and_realtime(db, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

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

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    conversation_id = conversation.id
    assign_conversation(
        db,
        company_id=company.id,
        conversation_id=conversation_id,
        assigned_user_id=owner.id,
        actor_user=owner,
    )

    assigned = db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    assert assigned is not None
    assert assigned.status == "waiting_human"

    published: list[tuple[str, dict]] = []

    def capture_publish(company_id, event_type, payload):
        published.append((event_type, payload))

    monkeypatch.setattr("app.conversations.service.realtime_manager.publish", capture_publish)
    monkeypatch.setattr("app.whatsapp.service.realtime_manager.publish", capture_publish)

    paused_conversation = set_conversation_ai_enabled(
        db,
        company_id=company.id,
        conversation_id=conversation_id,
        ai_enabled=False,
        actor_user=owner,
    )
    assert paused_conversation.ai_enabled is False

    stored = db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    assert stored is not None
    assert stored.ai_enabled is False

    assert "conversation.ai_paused" in [event_type for event_type, _ in published]

    monkeypatch.setattr(
        "app.whatsapp.service.generate_auto_reply",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("No debe responder IA")),
    )

    webhook_db = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)()
    try:
        conversations = list(
            webhook_db.scalars(
                select(Conversation).where(
                    Conversation.company_id == company.id,
                    Conversation.contact_id == contact.id,
                    Conversation.channel == "whatsapp",
                )
            )
        )
        assert len(conversations) == 1
        assert conversations[0].status == "waiting_human"
        assert (
            webhook_db.scalar(
                select(Conversation.ai_enabled).where(Conversation.id == conversation_id)
            )
            is False
        )
        processed, skipped = process_webhook_payload(
            webhook_db,
            payload={
                "entry": [
                    {
                        "changes": [
                            {
                                "value": {
                                    "metadata": {"phone_number_id": "phone-1"},
                                    "contacts": [
                                        {
                                            "wa_id": "573001112233",
                                            "profile": {"name": "Cliente"},
                                        }
                                    ],
                                    "messages": [
                                        {
                                            "id": "wamid-paused-1",
                                            "from": "573001112233",
                                            "timestamp": "1710000000",
                                            "type": "text",
                                            "text": {"body": "Hola, quiero retomar"},
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                ]
            },
        )
    finally:
        webhook_db.close()
    assert processed == 1
    assert skipped == 0

    resume_called = False

    def capture_resume(*args, **kwargs):
        nonlocal resume_called
        resume_called = True
        return None

    monkeypatch.setattr("app.whatsapp.service.generate_auto_reply", capture_resume)

    resumed_conversation = set_conversation_ai_enabled(
        db,
        company_id=company.id,
        conversation_id=conversation_id,
        ai_enabled=True,
        actor_user=owner,
    )
    assert resumed_conversation.ai_enabled is True
    assert "conversation.ai_resumed" in [event_type for event_type, _ in published]

    webhook_db = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)()
    try:
        assert (
            webhook_db.scalar(
                select(Conversation.ai_enabled).where(Conversation.id == conversation_id)
            )
            is True
        )
        processed, skipped = process_webhook_payload(
            webhook_db,
            payload={
                "entry": [
                    {
                        "changes": [
                            {
                                "value": {
                                    "metadata": {"phone_number_id": "phone-1"},
                                    "contacts": [
                                        {
                                            "wa_id": "573001112233",
                                            "profile": {"name": "Cliente"},
                                        }
                                    ],
                                    "messages": [
                                        {
                                            "id": "wamid-resumed-1",
                                            "from": "573001112233",
                                            "timestamp": "1710000001",
                                            "type": "text",
                                            "text": {"body": "Ahora si"},
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                ]
            },
        )
    finally:
        webhook_db.close()
    assert processed == 1
    assert skipped == 0
    assert resume_called is True
    assert "conversation.ai_resumed" in [event_type for event_type, _ in published]


def test_mark_conversation_read_is_idempotent(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    append_message(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        sender_type="customer",
        content="Hola",
        external_message_id="wamid-read",
    )
    db.commit()

    mark_conversation_read(db, company_id=company.id, conversation_id=conversation.id)
    mark_conversation_read(db, company_id=company.id, conversation_id=conversation.id)

    detail_response = client.get(
        f"/api/v1/conversations/{conversation.id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["unread_count"] == 0
    assert [event["event_type"] for event in detail["events"]].count("conversation.read") == 1


def test_status_events_are_preserved_when_message_arrives_later(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
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

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-1"},
                                "statuses": [
                                    {
                                        "id": "wamid-race",
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

    append_message(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        sender_type="agent",
        content="Mensaje enviado",
        external_message_id="wamid-race",
    )
    db.commit()

    detail_response = client.get(
        f"/api/v1/conversations/{conversation.id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    status_events = [
        event for event in detail["events"] if event["event_type"] == "message.status"
    ]
    assert len(status_events) == 1
    assert status_events[0]["payload"]["message_id"] == "wamid-race"


def test_status_events_backfill_conversation_from_sent_message_event_when_message_row_missing(
    db,
):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
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
    create_event(
        db,
        company_id=company.id,
        event_type="message.sent",
        payload={
            "conversation_id": str(conversation.id),
            "contact_id": str(contact.id),
            "message_id": "local-message-id",
            "meta_message_id": "wamid-status-backfill",
            "source": "agent_manual",
        },
    )
    db.commit()

    processed, skipped = process_webhook_payload(
        db,
        payload={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "phone-1"},
                                "statuses": [
                                    {
                                        "id": "wamid-status-backfill",
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

    detail_events = list_conversation_events(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
    )
    status_events = [event for event in detail_events if event.event_type == "message.status"]
    assert len(status_events) == 1
    assert status_events[0].payload["conversation_id"] == str(conversation.id)
    assert status_events[0].payload["message_id"] == "wamid-status-backfill"


def test_prepare_appointment_intent_records_conversation_event(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )

    response = client.post(
        f"/api/v1/conversations/{conversation.id}/prepare-appointment",
        headers=auth_headers(owner),
    )
    assert response.status_code == 200
    prepared_context = response.json()
    assert prepared_context["conversation_id"] == str(conversation.id)
    assert prepared_context["contact_id"] == str(contact.id)
    assert prepared_context["contact_name"] == "Cliente"
    assert prepared_context["source"] == "inbox"
    assert prepared_context["prepared_at"] is not None

    detail_response = client.get(
        f"/api/v1/conversations/{conversation.id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    prepared_events = [
        event for event in detail["events"] if event["event_type"] == "conversation.appointment_intent_prepared"
    ]
    assert len(prepared_events) == 1
    prepared_event = prepared_events[0]
    assert prepared_event["payload"]["conversation_id"] == str(conversation.id)
    assert prepared_event["payload"]["contact_id"] == str(contact.id)
    assert prepared_event["payload"]["funnel_id"] == str(conversation.funnel_id)
    assert prepared_event["payload"]["contact_name"] == "Cliente"
    assert prepared_event["payload"]["funnel_name"] is not None
    assert prepared_event["payload"]["prepared_at"] is not None
    assert prepared_event["payload"]["source"] == "inbox"

    assign_conversation(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        assigned_user_id=owner.id,
    )
    assign_conversation_funnel(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        funnel_id=None,
        funnel_step_id=None,
        current_step="seguimiento",
    )
    response = client.post(
        f"/api/v1/conversations/{conversation.id}/prepare-appointment",
        headers=auth_headers(owner),
    )
    assert response.status_code == 200

    prepared_events = [
        event
        for event in list_conversation_events(
            db,
            company_id=company.id,
            conversation_id=conversation.id,
        )
        if event.event_type == "conversation.appointment_intent_prepared"
    ]
    assert len(prepared_events) == 2
    fixed_timestamp = datetime.now(UTC)
    fixed_timestamp_value = fixed_timestamp.isoformat()
    for event in prepared_events:
        event.created_at = fixed_timestamp
        event.payload["prepared_at"] = fixed_timestamp_value
    db.commit()

    context_response = client.get(
        f"/api/v1/conversations/{conversation.id}/appointment-intent",
        headers=auth_headers(owner),
    )
    assert context_response.status_code == 200
    context = context_response.json()
    second_context_response = client.get(
        f"/api/v1/conversations/{conversation.id}/appointment-intent",
        headers=auth_headers(owner),
    )
    assert second_context_response.status_code == 200
    assert second_context_response.json() == context

    selected_event = next(
        event
        for event in prepared_events
        if event.payload["funnel_id"] == context["funnel_id"]
        and event.payload["current_step"] == context["current_step"]
        and event.payload["assigned_user_id"] == context["assigned_user_id"]
    )
    assert context["conversation_id"] == str(conversation.id)
    assert context["contact_id"] == str(contact.id)
    assert context["contact_name"] == "Cliente"
    assert context["funnel_id"] == selected_event.payload["funnel_id"]
    assert context["funnel_name"] == selected_event.payload["funnel_name"]
    assert context["current_step"] == selected_event.payload["current_step"]
    assert context["assigned_user_id"] == selected_event.payload["assigned_user_id"]
    assert datetime.fromisoformat(context["prepared_at"].replace("Z", "+00:00")) == datetime.fromisoformat(
        selected_event.payload["prepared_at"].replace("Z", "+00:00")
    )


def test_get_appointment_intent_requires_prepared_context(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )

    response = client.get(
        f"/api/v1/conversations/{conversation.id}/appointment-intent",
        headers=auth_headers(owner),
    )
    assert response.status_code == 404


def test_get_appointment_availability_records_preference_selection_event(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    prepare_response = client.post(
        f"/api/v1/conversations/{conversation.id}/prepare-appointment",
        headers=auth_headers(owner),
    )
    assert prepare_response.status_code == 200

    availability_response = client.post(
        "/api/v1/appointments/availability",
        headers=auth_headers(owner),
        json={
            "preferred_period": "morning",
            "duration_minutes": 30,
            "horizon_days": 7,
            "max_options": 3,
            "conversation_id": str(conversation.id),
        },
    )

    assert availability_response.status_code == 200
    detail_response = client.get(
        f"/api/v1/conversations/{conversation.id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    preference_events = [
        event
        for event in detail_response.json()["events"]
        if event["event_type"] == "conversation.appointment_preference_selected"
    ]
    assert len(preference_events) == 1
    assert preference_events[0]["payload"]["preferred_period"] == "morning"


def test_prepare_appointment_intent_requires_inbox_permission(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente sin Inbox",
            email="no-inbox@acme.example.com",
            password="super-secret-11",
            role="agent",
            module_permissions={"inbox": False},
        ),
    )

    response = client.post(
        f"/api/v1/conversations/{conversation.id}/prepare-appointment",
        headers=auth_headers(agent),
    )
    assert response.status_code == 403


def test_prepare_appointment_intent_does_not_persist_until_confirmation(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )

    assert list(db.scalars(select(Appointment).where(Appointment.company_id == company.id))) == []

    response = client.post(
        f"/api/v1/conversations/{conversation.id}/prepare-appointment",
        headers=auth_headers(owner),
    )
    assert response.status_code == 200
    assert list(db.scalars(select(Appointment).where(Appointment.company_id == company.id))) == []


def test_create_appointment_persists_manual_cita_and_keeps_sync_honest_without_calendar(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        json={
            "contact_id": str(contact.id),
            "conversation_id": None,
            "assigned_user_id": None,
            "scheduled_at": datetime(2026, 6, 30, 11, 0, tzinfo=UTC).isoformat(),
            "duration_minutes": 45,
            "notes": "Cita manual",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["contact_id"] == str(contact.id)
    assert payload["conversation_id"] is None
    assert payload["calendar_sync_status"] is None
    assert payload["calendar_sync_error"] is None

    appointments = list(db.scalars(select(Appointment).where(Appointment.company_id == company.id)))
    assert len(appointments) == 1
    assert appointments[0].contact_id == contact.id
    assert appointments[0].calendar_sync_status is None

    list_response = client.get("/api/v1/appointments", headers=auth_headers(owner))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_list_appointments_filters_by_date_status_contact_assignee_and_source(db, client):
    company, owner = bootstrap_company(db, "Acme")
    assistant = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Asesor",
            email="advisor@acme.example.com",
            password="super-secret-123",
            role="agent",
            module_permissions={"appointments": True},
        ),
    )
    first_contact = Contact(company_id=company.id, name="Cliente 1", phone="+573001112201")
    second_contact = Contact(company_id=company.id, name="Cliente 2", phone="+573001112202")
    third_contact = Contact(company_id=company.id, name="Cliente 3", phone="+573001112203")
    db.add_all([first_contact, second_contact, third_contact])
    db.commit()

    inbox_conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=second_contact.id, channel="whatsapp"),
    )

    manual_early = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=first_contact.id,
            conversation_id=None,
            assigned_user_id=owner.id,
            scheduled_at=datetime(2026, 7, 10, 10, 0, tzinfo=UTC),
            duration_minutes=30,
            notes="manual-early",
        ),
    )
    target = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=second_contact.id,
            conversation_id=inbox_conversation.id,
            assigned_user_id=assistant.id,
            scheduled_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
            duration_minutes=45,
            notes="inbox-target",
        ),
    )
    manual_late = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=third_contact.id,
            conversation_id=None,
            assigned_user_id=assistant.id,
            scheduled_at=datetime(2026, 7, 12, 10, 0, tzinfo=UTC),
            duration_minutes=30,
            notes="manual-late",
        ),
    )

    update_appointment(
        db,
        company_id=company.id,
        appointment_id=target.id,
        payload=AppointmentUpdate(status="cancelled"),
    )

    response = client.get(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        params={
            "scheduled_from": "2026-07-11",
            "scheduled_to": "2026-07-11",
            "status": "cancelled",
            "contact_id": str(second_contact.id),
            "assigned_user_id": str(assistant.id),
            "source": "inbox",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(target.id)
    assert payload[0]["conversation_id"] == str(inbox_conversation.id)
    assert payload[0]["status"] == "cancelled"


def test_list_appointments_keeps_focused_row_when_filtered(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112211")
    db.add(contact)
    db.commit()

    earliest = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            conversation_id=None,
            assigned_user_id=None,
            scheduled_at=datetime(2026, 7, 13, 9, 0, tzinfo=UTC),
            duration_minutes=30,
            notes="primer turno",
        ),
    )
    focused = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            conversation_id=None,
            assigned_user_id=None,
            scheduled_at=datetime(2026, 7, 14, 9, 0, tzinfo=UTC),
            duration_minutes=30,
            notes="turno enfocado",
        ),
    )

    response = client.get(
        f"/api/v1/appointments?limit=1&offset=0&scheduled_from=2026-07-13&scheduled_to=2026-07-14&source=manual&focus_appointment_id={focused.id}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(focused.id)
    assert payload[0]["notes"] == "turno enfocado"
    assert payload[0]["conversation_id"] is None
    assert payload[0]["id"] != str(earliest.id)


def test_create_appointment_uses_configured_default_duration_when_missing(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

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
                        "weekend": {"start": "10:00", "end": "13:00"},
                        "default_appointment_duration_minutes": 45,
                    }
                }
            },
            active=True,
        ),
    )

    response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        json={
            "contact_id": str(contact.id),
            "conversation_id": None,
            "assigned_user_id": None,
            "scheduled_at": datetime(2026, 6, 30, 16, 0, tzinfo=UTC).isoformat(),
            "notes": "Cita con duración por defecto",
        },
    )

    assert response.status_code == 201
    assert response.json()["duration_minutes"] == 45


def test_list_appointments_orders_by_scheduled_at_ascending(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    later_slot = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)
    earlier_slot = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)

    later_response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        json={
            "contact_id": str(contact.id),
            "conversation_id": None,
            "assigned_user_id": None,
            "scheduled_at": later_slot.isoformat(),
            "duration_minutes": 30,
            "notes": "Cita posterior",
        },
    )
    assert later_response.status_code == 201
    earlier_response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        json={
            "contact_id": str(contact.id),
            "conversation_id": None,
            "assigned_user_id": None,
            "scheduled_at": earlier_slot.isoformat(),
            "duration_minutes": 30,
            "notes": "Cita anterior",
        },
    )
    assert earlier_response.status_code == 201

    response = client.get("/api/v1/appointments", headers=auth_headers(owner))
    assert response.status_code == 200
    payload = response.json()
    assert [item["notes"] for item in payload[:2]] == ["Cita anterior", "Cita posterior"]


def test_list_appointments_can_focus_out_of_page_appointment(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    earlier_slot = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)
    later_slot = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)

    earlier_response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        json={
            "contact_id": str(contact.id),
            "conversation_id": None,
            "assigned_user_id": None,
            "scheduled_at": earlier_slot.isoformat(),
            "duration_minutes": 30,
            "notes": "Cita anterior",
        },
    )
    assert earlier_response.status_code == 201
    later_response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        json={
            "contact_id": str(contact.id),
            "conversation_id": None,
            "assigned_user_id": None,
            "scheduled_at": later_slot.isoformat(),
            "duration_minutes": 30,
            "notes": "Cita posterior",
        },
    )
    assert later_response.status_code == 201
    focus_id = later_response.json()["id"]

    response = client.get(
        f"/api/v1/appointments?limit=1&offset=0&focus_appointment_id={focus_id}",
        headers=auth_headers(owner),
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["notes"] for item in payload] == ["Cita posterior"]


def test_create_appointment_links_inbox_context_and_reflects_in_conversation_events(
    db, client, monkeypatch
):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente Inbox", phone="+573001112233")
    db.add(contact)
    db.commit()

    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    monkeypatch.setattr(
        "app.appointments.service.sync_appointment_with_calendar",
        lambda *args, **kwargs: SimpleNamespace(external_event_id="calendar-1", raw={"provider": "mock"}),
    )

    response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        json={
            "contact_id": str(contact.id),
            "conversation_id": str(conversation.id),
            "assigned_user_id": None,
            "scheduled_at": datetime(2026, 6, 30, 12, 0, tzinfo=UTC).isoformat(),
            "duration_minutes": 30,
            "notes": "Cita desde inbox",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["conversation_id"] == str(conversation.id)

    detail_response = client.get(
        f"/api/v1/conversations/{conversation.id}",
        headers=auth_headers(owner),
    )
    assert detail_response.status_code == 200
    event_types = [event["event_type"] for event in detail_response.json()["events"]]
    assert "appointment.created" in event_types

    appointment_id = payload["id"]
    update_response = client.put(
        f"/api/v1/appointments/{appointment_id}",
        headers=auth_headers(owner),
        json={
            "notes": "Cita actualizada desde inbox",
        },
    )

    assert update_response.status_code == 200

    updated_detail_response = client.get(
        f"/api/v1/conversations/{conversation.id}",
        headers=auth_headers(owner),
    )
    assert updated_detail_response.status_code == 200
    updated_event_types = [event["event_type"] for event in updated_detail_response.json()["events"]]
    assert "appointment.updated" in updated_event_types


def test_create_appointment_rejects_overlapping_busy_slot(db):
    company, _owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            conversation_id=None,
            assigned_user_id=None,
            scheduled_at=datetime(2026, 6, 30, 9, 0, tzinfo=UTC),
            duration_minutes=60,
            notes="Cita existente",
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        create_appointment(
            db,
            company_id=company.id,
            payload=AppointmentCreate(
                contact_id=contact.id,
                conversation_id=None,
                assigned_user_id=None,
                scheduled_at=datetime(2026, 6, 30, 9, 30, tzinfo=UTC),
                duration_minutes=30,
                notes="Solapa con la anterior",
            ),
        )
    assert exc_info.value.status_code == 409


def test_create_appointment_rejects_outside_operational_hours(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        json={
            "contact_id": str(contact.id),
            "conversation_id": None,
            "assigned_user_id": None,
            "scheduled_at": datetime(2026, 6, 30, 2, 0, tzinfo=UTC).isoformat(),
            "duration_minutes": 30,
            "notes": "Fuera de horario",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Appointment slot is outside operational hours"
    assert list(db.scalars(select(Appointment).where(Appointment.company_id == company.id))) == []


def test_create_appointment_rejects_cross_tenant_contact_and_does_not_persist_partial_row(db, client):
    company, owner = bootstrap_company(db, "Acme")
    other_company, _ = bootstrap_company(db, "Bravo")
    other_contact = Contact(company_id=other_company.id, name="Cliente Ajeno", phone="+573001112244")
    db.add(other_contact)
    db.commit()

    response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(owner),
        json={
            "contact_id": str(other_contact.id),
            "conversation_id": None,
            "assigned_user_id": None,
            "scheduled_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "duration_minutes": 30,
            "notes": "No debe crearse",
        },
    )

    assert response.status_code == 404
    assert list(db.scalars(select(Appointment).where(Appointment.company_id == company.id))) == []
    assert list(db.scalars(select(Appointment).where(Appointment.company_id == other_company.id))) == []


def test_create_appointment_requires_appointments_permission(db, client):
    company, _ = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente sin agenda",
            email="no-appointments@acme.example.com",
            password="super-secret-12",
            role="agent",
            module_permissions={"appointments": False},
        ),
    )

    response = client.post(
        "/api/v1/appointments",
        headers=auth_headers(agent),
        json={
            "contact_id": str(contact.id),
            "conversation_id": None,
            "assigned_user_id": None,
            "scheduled_at": datetime(2026, 6, 30, 11, 30, tzinfo=UTC).isoformat(),
            "duration_minutes": 30,
            "notes": "No debe crearse",
        },
    )

    assert response.status_code == 403
    assert list(db.scalars(select(Appointment).where(Appointment.company_id == company.id))) == []


def test_get_appointment_availability_prefers_real_slots_from_internal_busy_intervals(db, client):
    company, owner = bootstrap_company(db, "Acme")
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112233")
    db.add(contact)
    db.commit()

    tomorrow_busy_start = (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=8, minute=0, second=0, microsecond=0
    )
    db.add(
        Appointment(
            company_id=company.id,
            contact_id=contact.id,
            scheduled_at=tomorrow_busy_start,
            duration_minutes=60,
            status="scheduled",
        )
    )
    db.commit()

    response = client.post(
        "/api/v1/appointments/availability",
        headers=auth_headers(owner),
        json={
            "preferred_period": "morning",
            "duration_minutes": 60,
            "horizon_days": 7,
            "max_options": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_source"] == "internal"
    assert payload["calendar_integration_active"] is False
    assert len(payload["options"]) == 3
    option_dates = {
        datetime.fromisoformat(option["scheduled_at"]).astimezone(UTC).date()
        for option in payload["options"]
    }
    assert len(option_dates) == 3
    first_slot = datetime.fromisoformat(payload["options"][0]["scheduled_at"]).astimezone(UTC)
    assert first_slot == tomorrow_busy_start + timedelta(hours=1)


def test_get_appointment_availability_uses_calendar_busy_intervals_when_available(db, client, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")

    busy_start = (datetime.now(UTC) + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    busy_intervals = [(busy_start, busy_start + timedelta(hours=2))]

    monkeypatch.setattr(
        "app.appointments.service._collect_calendar_busy_intervals",
        lambda *args, **kwargs: (busy_intervals, True, None),
    )

    response = client.post(
        "/api/v1/appointments/availability",
        headers=auth_headers(owner),
        json={
            "preferred_period": "morning",
            "duration_minutes": 60,
            "horizon_days": 7,
            "max_options": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_source"] == "external"
    assert payload["calendar_integration_active"] is True
    first_slot = datetime.fromisoformat(payload["options"][0]["scheduled_at"]).astimezone(UTC)
    assert first_slot == busy_start + timedelta(hours=2)


def test_get_appointment_availability_falls_back_when_calendar_lookup_fails(db, client, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")

    monkeypatch.setattr(
        "app.appointments.service._collect_calendar_busy_intervals",
        lambda *args, **kwargs: ([], True, "Calendario temporalmente indisponible"),
    )

    response = client.post(
        "/api/v1/appointments/availability",
        headers=auth_headers(owner),
        json={
            "preferred_period": "afternoon",
            "duration_minutes": 60,
            "horizon_days": 7,
            "max_options": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_source"] == "internal_fallback"
    assert payload["validation_error"] == "Calendario temporalmente indisponible"
    assert payload["calendar_integration_active"] is True
    assert len(payload["options"]) == 3

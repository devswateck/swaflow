from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Generator
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.audit.service import list_audit_logs
from app.auth.service import build_token
from app.companies.schemas import CompanyCreate, CompanyUpdate
from app.companies.service import create_company_with_owner, update_company
from app.core.crypto import decrypt_secret
from app.core.database import Base, get_db
from app.core.schemas import OwnerCreate
from app.main import app
from app.contacts.models import Contact
from app.conversations.models import Conversation
from app.inventory.models import Inventory
from app.messages.models import Message
from app.products.models import Product
from app.products.schemas import ProductCreate, ProductUpdate
from app.products.service import create_product, update_product
from app.users.schemas import UserCreate
from app.users.service import create_user
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.schemas import WhatsAppAccountCreate, WhatsAppSendProductCardsFromDbRequest, WhatsAppSendProductCardsRequest
from app.whatsapp.service import (
    _product_card_caption,
    create_account,
    send_product_cards_from_db,
    send_product_cards_message,
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


def auth_headers(user) -> dict[str, str]:
    return {"Authorization": f"Bearer {build_token(user)}"}


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


def test_whatsapp_setup_and_account_lifecycle_exposes_honest_configuration(db, client, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")
    settings = SimpleNamespace(
        public_base_url="https://swaflow.example/",
        whatsapp_verify_token="global-verify-token",
        whatsapp_app_secret="webhook-secret",
        whatsapp_graph_api_version="v26.0",
    )
    monkeypatch.setattr("app.whatsapp.routes.get_settings", lambda: settings)
    monkeypatch.setattr("app.whatsapp.service.get_settings", lambda: settings)

    setup_response = client.get("/api/v1/whatsapp/setup", headers=auth_headers(owner))
    assert setup_response.status_code == 200
    assert setup_response.json() == {
        "callback_url": "https://swaflow.example/api/v1/webhooks/whatsapp",
        "verify_token": "global-verify-token",
        "graph_api_version": "v26.0",
        "app_secret_configured": True,
    }

    create_response = client.post(
        "/api/v1/whatsapp/accounts",
        headers=auth_headers(owner),
        json={
            "phone_number_id": "phone-number-id-1",
            "business_account_id": "business-account-id-1",
            "access_token": "EAA-test-access-token",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["company_id"] == str(company.id)
    assert created["phone_number_id"] == "phone-number-id-1"
    assert created["business_account_id"] == "business-account-id-1"
    assert created["verify_token"] == "global-verify-token"
    assert created["status"] == "active"
    assert "access_token" not in created

    stored_account = db.scalar(select(WhatsAppAccount).where(WhatsAppAccount.id == UUID(created["id"])))
    assert stored_account is not None
    assert stored_account.access_token_encrypted != "EAA-test-access-token"
    assert decrypt_secret(stored_account.access_token_encrypted) == "EAA-test-access-token"

    list_response = client.get("/api/v1/whatsapp/accounts", headers=auth_headers(owner))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == created["id"]

    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {
            "id": "phone-number-id-1",
            "display_phone_number": "+57 300 111 2233",
            "verified_name": "Acme Support",
            "quality_rating": "green",
        },
    )
    test_response = client.post(
        f"/api/v1/whatsapp/accounts/{created['id']}/test",
        headers=auth_headers(owner),
    )
    assert test_response.status_code == 200
    assert test_response.json() == {
        "ok": True,
        "phone_number_id": "phone-number-id-1",
        "display_phone_number": "+57 300 111 2233",
        "verified_name": "Acme Support",
        "quality_rating": "green",
        "raw": {
            "id": "phone-number-id-1",
            "display_phone_number": "+57 300 111 2233",
            "verified_name": "Acme Support",
            "quality_rating": "green",
        },
    }


def test_whatsapp_webhook_verification_prefers_global_token_over_account_tokens(
    db, client, monkeypatch
):
    company, owner = bootstrap_company(db, "Acme")
    settings_with_global_token = SimpleNamespace(
        public_base_url="https://swaflow.example",
        whatsapp_verify_token="global-token",
        whatsapp_app_secret=None,
        whatsapp_graph_api_version="v26.0",
    )
    monkeypatch.setattr("app.whatsapp.routes.get_settings", lambda: settings_with_global_token)

    global_response = client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "global-token",
            "hub.challenge": "challenge-123",
        },
    )
    assert global_response.status_code == 200
    assert global_response.text == "challenge-123"

    invalid_response = client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "challenge-123",
        },
    )
    assert invalid_response.status_code == 403

    account = create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-number-id-2",
            business_account_id="business-account-id-2",
            access_token="EAA-account-token",
            verify_token="account-token",
        ),
    )
    assert account.verify_token == "account-token"

    account_token_rejected = client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "account-token",
            "hub.challenge": "challenge-456",
        },
    )
    assert account_token_rejected.status_code == 403

    account_token_settings = SimpleNamespace(
        public_base_url="https://swaflow.example",
        whatsapp_verify_token=None,
        whatsapp_app_secret=None,
        whatsapp_graph_api_version="v26.0",
    )
    monkeypatch.setattr("app.whatsapp.routes.get_settings", lambda: account_token_settings)

    account_response = client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "account-token",
            "hub.challenge": "challenge-456",
        },
    )
    assert account_response.status_code == 200
    assert account_response.text == "challenge-456"


def test_whatsapp_webhook_signature_validation_enforces_secret(db, client, monkeypatch):
    settings = SimpleNamespace(
        public_base_url="https://swaflow.example",
        whatsapp_verify_token=None,
        whatsapp_app_secret="webhook-secret",
        whatsapp_graph_api_version="v26.0",
    )
    monkeypatch.setattr("app.whatsapp.routes.get_settings", lambda: settings)
    monkeypatch.setattr("app.whatsapp.service.process_webhook_payload", lambda *args, **kwargs: (2, 1))

    body = b'{"entry":[{"changes":[{"value":{"metadata":{"phone_number_id":"phone-number-id-1"},"messages":[]}}]}]}'
    digest = hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()
    valid_signature = f"sha256={digest}"

    valid_response = client.post(
        "/api/v1/webhooks/whatsapp",
        content=body,
        headers={"x-hub-signature-256": valid_signature},
    )
    assert valid_response.status_code == 200
    assert valid_response.json() == {"processed": 2, "skipped": 1}

    missing_signature_response = client.post(
        "/api/v1/webhooks/whatsapp",
        content=body,
    )
    assert missing_signature_response.status_code == 401

    invalid_signature_response = client.post(
        "/api/v1/webhooks/whatsapp",
        content=body,
        headers={"x-hub-signature-256": "sha256=invalid"},
    )
    assert invalid_signature_response.status_code == 401


def test_whatsapp_webhook_processes_inbound_message_and_links_tenant_contact_conversation(
    db, client, monkeypatch
):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente principal",
            email="agent@acme.example.com",
            password="super-secret-11",
            role="agent",
        ),
    )
    account = create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-number-id-4",
            business_account_id="business-account-id-4",
            access_token="EAA-inbound-token",
            verify_token="tenant-token",
        ),
    )
    settings = SimpleNamespace(
        public_base_url="https://swaflow.example",
        whatsapp_verify_token=None,
        whatsapp_app_secret="webhook-secret",
        whatsapp_graph_api_version="v26.0",
    )
    monkeypatch.setattr("app.whatsapp.routes.get_settings", lambda: settings)
    monkeypatch.setattr("app.whatsapp.service.generate_auto_reply", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.whatsapp.service.realtime_manager.publish", lambda *args, **kwargs: None)

    body = json.dumps(
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": account.phone_number_id},
                                "contacts": [
                                    {
                                        "wa_id": "573001112233",
                                        "profile": {"name": "Camilo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "573001112233",
                                        "id": "wamid-inbound-1",
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
        }
    ).encode()
    digest = hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/v1/webhooks/whatsapp",
        content=body,
        headers={"x-hub-signature-256": f"sha256={digest}"},
    )

    assert response.status_code == 200
    assert response.json() == {"processed": 1, "skipped": 0}

    contact = db.scalar(
        select(Contact).where(Contact.company_id == company.id, Contact.phone == "573001112233")
    )
    assert contact is not None
    assert contact.name == "Camilo"
    assert contact.metadata_json == {"whatsapp": {"phone_number_id": account.phone_number_id}}

    conversation = db.scalar(
        select(Conversation).where(
            Conversation.company_id == company.id,
            Conversation.contact_id == contact.id,
            Conversation.channel == "whatsapp",
        )
    )
    assert conversation is not None
    assert conversation.unread_count == 1
    assert conversation.assigned_user_id == agent.id
    assert conversation.status == "waiting_human"

    audit_log = next(
        log
        for log in list_audit_logs(db, company_id=company.id, limit=10, offset=0)
        if log.action == "conversation.assigned"
    )
    assert audit_log.entity_id == conversation.id

    message = db.scalar(
        select(Message).where(
            Message.company_id == company.id,
            Message.conversation_id == conversation.id,
            Message.external_message_id == "wamid-inbound-1",
        )
    )
    assert message is not None
    assert message.sender_type == "customer"
    assert message.message_type == "text"
    assert message.content == "Hola"


def test_whatsapp_webhook_leaves_chat_unassigned_when_only_candidate_lacks_inbox_access(
    db, client, monkeypatch
):
    company, owner = bootstrap_company(db, "Acme")
    create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente sin inbox",
            email="agent-no-inbox@acme.example.com",
            password="super-secret-11",
            role="agent",
            module_permissions={"inbox": False},
        ),
    )
    update_company(
        db,
        company_id=company.id,
        current_company_id=company.id,
        payload=CompanyUpdate(auto_assign_single_additional_user_chats=True),
        actor_user=owner,
    )
    account = create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-number-id-5",
            business_account_id="business-account-id-5",
            access_token="EAA-inbound-token",
            verify_token="tenant-token",
        ),
    )
    settings = SimpleNamespace(
        public_base_url="https://swaflow.example",
        whatsapp_verify_token=None,
        whatsapp_app_secret="webhook-secret",
        whatsapp_graph_api_version="v26.0",
    )
    monkeypatch.setattr("app.whatsapp.routes.get_settings", lambda: settings)
    monkeypatch.setattr("app.whatsapp.service.generate_auto_reply", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.whatsapp.service.realtime_manager.publish", lambda *args, **kwargs: None)

    body = json.dumps(
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": account.phone_number_id},
                                "contacts": [
                                    {
                                        "wa_id": "573001112244",
                                        "profile": {"name": "Camilo"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "573001112244",
                                        "id": "wamid-inbound-2",
                                        "timestamp": "1710000001",
                                        "type": "text",
                                        "text": {"body": "Hola"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        }
    ).encode()
    digest = hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/v1/webhooks/whatsapp",
        content=body,
        headers={"x-hub-signature-256": f"sha256={digest}"},
    )

    assert response.status_code == 200
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.company_id == company.id,
            Conversation.channel == "whatsapp",
        )
    )
    assert conversation is not None
    assert conversation.assigned_user_id is None
    assert conversation.status == "open"


def test_whatsapp_manual_send_auto_assigns_single_inbox_user(db, client, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente Inbox",
            email="agent-inbox@acme.example.com",
            password="super-secret-12",
            role="agent",
        ),
    )
    update_company(
        db,
        company_id=company.id,
        current_company_id=company.id,
        payload=CompanyUpdate(auto_assign_single_additional_user_chats=True),
        actor_user=owner,
    )
    account = create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-number-id-6",
            business_account_id="business-account-id-6",
            access_token="EAA-manual-token",
            verify_token="tenant-token",
        ),
    )
    published: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        "app.whatsapp.service._meta_request",
        lambda *args, **kwargs: {"messages": [{"id": "wamid-manual-send-1"}]},
    )
    monkeypatch.setattr(
        "app.whatsapp.service.realtime_manager.publish",
        lambda company_id, event_type, payload: published.append((event_type, payload)),
    )

    response = client.post(
        "/api/v1/whatsapp/messages",
        headers=auth_headers(owner),
        json={
            "to": "+573001112255",
            "body": "Hola, confirmo tu cita",
            "account_id": str(account.id),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["meta_message_id"] == "wamid-manual-send-1"

    conversation = db.scalar(
        select(Conversation).where(Conversation.id == UUID(payload["conversation_id"]))
    )
    assert conversation is not None
    assert conversation.assigned_user_id == agent.id
    assert conversation.status == "waiting_human"
    assert [event_type for event_type, _payload in published] == [
        "conversation.assigned",
        "message.sent",
    ]

    audit_log = next(
        log
        for log in list_audit_logs(db, company_id=company.id, limit=10, offset=0)
        if log.action == "conversation.assigned"
    )
    assert audit_log.entity_id == conversation.id


def test_whatsapp_account_test_endpoint_returns_404_for_other_tenant(db, client, monkeypatch):
    company_a, _ = bootstrap_company(db, "Acme")
    _, owner_b = bootstrap_company(db, "Beta")
    monkeypatch.setattr(
        "app.whatsapp.service.get_settings",
        lambda: SimpleNamespace(
            public_base_url="https://swaflow.example",
            whatsapp_verify_token=None,
            whatsapp_app_secret=None,
            whatsapp_graph_api_version="v26.0",
        ),
    )

    account = create_account(
        db,
        company_id=company_a.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-number-id-3",
            business_account_id="business-account-id-3",
            access_token="EAA-cross-tenant-token",
            verify_token="tenant-token",
        ),
    )

    response = client.post(
        f"/api/v1/whatsapp/accounts/{account.id}/test",
        headers=auth_headers(owner_b),
    )
    assert response.status_code == 404


def test_whatsapp_setup_returns_403_for_same_tenant_user_without_module_permission(db, client, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente Acme",
            email="agent-whatsapp@acme.example.com",
            password="super-secret-agent",
            role="agent",
        ),
    )
    monkeypatch.setattr(
        "app.whatsapp.routes.get_settings",
        lambda: SimpleNamespace(
            public_base_url="https://swaflow.example",
            whatsapp_verify_token=None,
            whatsapp_app_secret=None,
            whatsapp_graph_api_version="v26.0",
        ),
    )

    response = client.get("/api/v1/whatsapp/setup", headers=auth_headers(agent))

    assert response.status_code == 403


def test_whatsapp_catalog_sync_rejects_invalid_catalog_ids_with_clear_message(
    db, client, monkeypatch
):
    company, owner = bootstrap_company(db, "Acme")
    account = create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-number-id-7",
            business_account_id="business-account-id-7",
            access_token="EAA-sync-token",
            verify_token="tenant-token",
        ),
    )
    monkeypatch.setattr(
        "app.whatsapp.service._fetch_catalog_product_rows",
        lambda **_kwargs: (_ for _ in ()).throw(
            HTTPException(status_code=400, detail="(#100) nonexisting field (products)")
        ),
    )

    response = client.post(
        "/api/v1/whatsapp/catalog/sync",
        headers=auth_headers(owner),
        json={"account_id": str(account.id), "catalog_id": "all-products"},
    )

    assert response.status_code == 400
    assert "usar el ID del catalogo" in response.json()["detail"]


def test_whatsapp_catalog_sync_returns_404_for_other_tenant_account(db, client):
    company_a, _ = bootstrap_company(db, "Acme")
    _, owner_b = bootstrap_company(db, "Beta")
    account = create_account(
        db,
        company_id=company_a.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-number-id-8",
            business_account_id="business-account-id-8",
            access_token="EAA-cross-tenant-token",
            verify_token="tenant-token",
        ),
    )

    response = client.post(
        "/api/v1/whatsapp/catalog/sync",
        headers=auth_headers(owner_b),
        json={"account_id": str(account.id), "catalog_id": "catalog-1"},
    )

    assert response.status_code == 404


def test_whatsapp_catalog_sync_returns_403_when_user_lacks_module_access(db, client):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente sin WhatsApp",
            email="agent-nowhatsapp@acme.example.com",
            password="super-secret-13",
            role="agent",
            module_permissions={"whatsapp": False},
        ),
    )

    response = client.post(
        "/api/v1/whatsapp/catalog/sync",
        headers=auth_headers(agent),
        json={"catalog_id": "catalog-1"},
    )

    assert response.status_code == 403


def test_product_service_blocks_manual_meta_mappings(db):
    company, _ = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as create_exc:
        create_product(
            db,
            company_id=company.id,
            payload=ProductCreate(
                name="Producto manual",
                price=130000,
                whatsapp_catalog_id="catalog-1",
                whatsapp_product_retailer_id="ret-1",
            ),
        )

    assert create_exc.value.status_code == 422
    assert "sincronizacion de catalogo" in str(create_exc.value.detail)

    blank_product = create_product(
        db,
        company_id=company.id,
        payload=ProductCreate(
            name="Producto manual",
            price=130000,
            whatsapp_catalog_id="   ",
            whatsapp_product_retailer_id="",
        ),
    )
    assert blank_product.whatsapp_catalog_id is None
    assert blank_product.whatsapp_product_retailer_id is None

    synced_product = Product(
        company_id=company.id,
        name="Producto sincronizado",
        price=130000,
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="ret-1",
    )
    db.add(synced_product)
    db.commit()

    updated_product = update_product(
        db,
        company_id=company.id,
        product_id=synced_product.id,
        payload=ProductUpdate(name="Nuevo nombre"),
    )
    assert updated_product.name == "Nuevo nombre"
    assert updated_product.whatsapp_catalog_id == "catalog-1"

    with pytest.raises(HTTPException) as update_exc:
        update_product(
            db,
            company_id=company.id,
            product_id=synced_product.id,
            payload=ProductUpdate(whatsapp_catalog_id="catalog-2"),
        )

    assert update_exc.value.status_code == 422
    assert "sincronizacion de catalogo" in str(update_exc.value.detail)


def test_product_card_caption_uses_available_units(db):
    company, _ = bootstrap_company(db, "Acme")
    product = Product(
        company_id=company.id,
        name="Producto con reserva",
        description="Descripcion breve",
        price=130000,
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="ret-1",
    )
    db.add(product)
    db.flush()
    inventory = Inventory(
        company_id=company.id,
        product_id=product.id,
        quantity_available=6,
        quantity_reserved=2,
    )
    db.add(inventory)
    db.commit()

    caption = _product_card_caption(product, inventory)

    assert "Disponible: 4 unidades" in caption


def test_whatsapp_product_cards_from_db_rejects_unavailable_products(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    account = create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-number-id-1",
            business_account_id="business-account-id-1",
            access_token="EAA-test-access-token",
            verify_token="tenant-token",
        ),
    )
    available = Product(
        company_id=company.id,
        name="Producto disponible",
        price=130000,
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="ret-available",
    )
    unavailable = Product(
        company_id=company.id,
        name="Producto sin stock",
        price=130000,
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="ret-unavailable",
    )
    db.add_all([available, unavailable])
    db.flush()
    db.add_all(
        [
            Inventory(
                company_id=company.id,
                product_id=available.id,
                quantity_available=3,
                quantity_reserved=0,
            ),
            Inventory(
                company_id=company.id,
                product_id=unavailable.id,
                quantity_available=1,
                quantity_reserved=1,
            ),
        ]
    )
    db.commit()
    monkeypatch.setattr(
        "app.whatsapp.service._send_interactive_with_account",
        lambda *_args, **_kwargs: pytest.fail("No debe enviar tarjetas cuando hay productos sin stock"),
    )

    with pytest.raises(HTTPException) as exc_info:
        send_product_cards_from_db(
            db,
            company_id=company.id,
            payload=WhatsAppSendProductCardsFromDbRequest(
                to="573001112233",
                body="Te comparto opciones",
                product_ids=[available.id, unavailable.id],
                account_id=account.id,
            ),
        )

    assert exc_info.value.status_code == 422
    assert "confirmed stock" in str(exc_info.value.detail)


def test_whatsapp_manual_product_cards_rejects_unavailable_products(db, monkeypatch):
    company, _ = bootstrap_company(db, "Acme")
    account = create_account(
        db,
        company_id=company.id,
        payload=WhatsAppAccountCreate(
            phone_number_id="phone-number-id-2",
            business_account_id="business-account-id-2",
            access_token="EAA-test-access-token",
            verify_token="tenant-token",
        ),
    )
    product = Product(
        company_id=company.id,
        name="Producto sin stock",
        price=130000,
        currency="COP",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="ret-unavailable",
    )
    db.add(product)
    db.flush()
    db.add(
        Inventory(
            company_id=company.id,
            product_id=product.id,
            quantity_available=1,
            quantity_reserved=1,
        )
    )
    db.commit()
    monkeypatch.setattr(
        "app.whatsapp.service._send_interactive_with_account",
        lambda *_args, **_kwargs: pytest.fail("No debe enviar tarjetas cuando no hay stock"),
    )

    with pytest.raises(HTTPException) as exc_info:
        send_product_cards_message(
            db,
            company_id=company.id,
            payload=WhatsAppSendProductCardsRequest(
                to="573001112233",
                body="Te comparto opciones",
                catalog_id="catalog-1",
                items=[{"product_retailer_id": "ret-unavailable"}],
                account_id=account.id,
            ),
        )

    assert exc_info.value.status_code == 422
    assert "confirmed stock" in str(exc_info.value.detail)

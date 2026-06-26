from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Generator
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.auth.service import build_token
from app.companies.schemas import CompanyCreate
from app.companies.service import create_company_with_owner
from app.core.crypto import decrypt_secret
from app.core.database import Base, get_db
from app.core.schemas import OwnerCreate
from app.main import app
from app.contacts.models import Contact
from app.conversations.models import Conversation
from app.messages.models import Message
from app.users.schemas import UserCreate
from app.users.service import create_user
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.schemas import WhatsAppAccountCreate
from app.whatsapp.service import create_account


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
        "callback_url": "https://swaflow.example/webhooks/whatsapp",
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

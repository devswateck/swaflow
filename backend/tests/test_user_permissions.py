from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth.service import build_current_user_payload, build_token
from app.companies.service import create_company_with_owner, update_company
from app.companies.schemas import CompanyCreate, CompanyUpdate
from app.contacts.models import Contact
from app.core.database import get_db
from app.core.schemas import OwnerCreate
from app.main import app
from app.conversations.schemas import ConversationCreate
from app.conversations.service import assign_conversation, create_conversation
from app.users.permissions import can_access_module, default_module_permissions, ensure_module_access
from app.users.schemas import UserCreate, UserPasswordReset, UserUpdate
from app.users.service import create_user, deactivate_user, get_user, reset_user_password, update_user


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


def test_additional_user_defaults_to_safe_modules(db):
    company, _ = bootstrap_company(db, "Acme")

    user = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente Acme",
            email="agent@acme.example.com",
            password="super-secret-1",
            role="agent",
        ),
    )

    assert user.role == "agent"
    assert user.module_permissions == default_module_permissions(role="agent")

    payload = build_current_user_payload(user)
    assert payload["module_permissions"] == default_module_permissions(role="agent")


def test_module_permissions_can_enable_restricted_access_without_changing_role(db):
    company, _ = bootstrap_company(db, "Acme")

    user = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente con permisos",
            email="agent-perms@acme.example.com",
            password="super-secret-2",
            role="agent",
            module_permissions={"whatsapp": True, "settings": True},
        ),
    )

    assert user.role == "agent"
    assert user.module_permissions["whatsapp"] is True
    assert user.module_permissions["settings"] is True
    assert can_access_module(user, "whatsapp") is True
    assert can_access_module(user, "settings") is True


def test_tenant_user_creation_rejects_privileged_roles(db):
    company, _ = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc:
        create_user(
            db,
            company_id=company.id,
            payload=UserCreate(
                name="Administrador Acme",
                email="admin@acme.example.com",
                password="super-secret-2",
                role="admin",
            ),
        )
    assert exc.value.status_code == 403


def test_existing_privileged_tenant_users_can_be_edited_without_changing_privilege(db):
    company, owner = bootstrap_company(db, "Acme")

    updated_owner = update_user(
        db,
        company_id=company.id,
        user_id=owner.id,
        payload=UserUpdate(name="Owner Renombrado", role="owner"),
    )

    assert updated_owner.name == "Owner Renombrado"
    assert updated_owner.role == "owner"

    admin = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Admin interno",
            email="admin@acme.example.com",
            password="super-secret-9",
            role="agent",
        ),
    )
    admin.role = "admin"
    db.commit()

    updated_admin = update_user(
        db,
        company_id=company.id,
        user_id=admin.id,
        payload=UserUpdate(name="Admin Renombrado", role="admin"),
    )

    assert updated_admin.name == "Admin Renombrado"
    assert updated_admin.role == "admin"


def test_role_demotion_resets_module_permissions_to_new_baseline(db):
    company, _ = bootstrap_company(db, "Acme")
    user = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Operador",
            email="operador@acme.example.com",
            password="super-secret-8",
            role="agent",
            module_permissions={"whatsapp": True, "settings": True},
        ),
    )

    demoted = update_user(
        db,
        company_id=company.id,
        user_id=user.id,
        payload=UserUpdate(role="viewer"),
    )

    assert demoted.role == "viewer"
    assert demoted.module_permissions == default_module_permissions(role="viewer")
    assert demoted.module_permissions["whatsapp"] is False
    assert demoted.module_permissions["settings"] is False

    with pytest.raises(HTTPException) as exc:
        create_user(
            db,
            company_id=company.id,
            payload=UserCreate(
                name="Propietario Acme",
                email="owner2@acme.example.com",
                password="super-secret-3",
                role="owner",
            ),
        )
    assert exc.value.status_code == 403


def test_user_update_rejects_unknown_status_values(db, client):
    company, owner = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente Acme",
            email="agent-status@acme.example.com",
            password="super-secret-10",
            role="agent",
        ),
    )

    headers = {"Authorization": f"Bearer {build_token(owner)}"}
    response = client.put(
        f"/api/v1/users/{agent.id}",
        headers=headers,
        json={"status": "paused"},
    )

    assert response.status_code == 422


def test_last_active_privileged_user_cannot_be_demoted(db):
    company, owner = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc:
        update_user(
            db,
            company_id=company.id,
            user_id=owner.id,
            payload=UserUpdate(role="agent"),
        )

    assert exc.value.status_code == 403


def test_last_active_privileged_user_guard_uses_row_lock(db, monkeypatch):
    company, owner = bootstrap_company(db, "Acme")
    seen_company_lock: list[bool] = []
    original_scalar = type(db).scalar

    def capture_scalar(self, statement, *args, **kwargs):
        raw_columns = getattr(statement, "_raw_columns", [])
        if raw_columns and getattr(raw_columns[0], "table", None) is not None:
            seen_company_lock.append(
                raw_columns[0].table.name == "companies"
                and getattr(statement, "_for_update_arg", None) is not None
            )
        return original_scalar(self, statement, *args, **kwargs)

    monkeypatch.setattr(type(db), "scalar", capture_scalar)

    with pytest.raises(HTTPException) as exc:
        update_user(
            db,
            company_id=company.id,
            user_id=owner.id,
            payload=UserUpdate(role="agent"),
        )

    assert exc.value.status_code == 403
    assert any(seen_company_lock)


def test_last_active_privileged_user_cannot_be_deactivated(db):
    company, owner = bootstrap_company(db, "Acme")

    with pytest.raises(HTTPException) as exc:
        deactivate_user(db, company_id=company.id, user_id=owner.id)

    assert exc.value.status_code == 403


def test_module_access_helper_blocks_restricted_backend_access(db):
    company, _ = bootstrap_company(db, "Acme")

    user = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente sin permisos",
            email="agent-no-perms@acme.example.com",
            password="super-secret-3",
            role="agent",
        ),
    )

    with pytest.raises(HTTPException) as exc:
        ensure_module_access(user, "whatsapp")

    assert exc.value.status_code == 403


def test_cross_tenant_user_operations_return_404(db):
    company_a, _ = bootstrap_company(db, "Acme")
    company_b, _ = bootstrap_company(db, "Beta")
    user = create_user(
        db,
        company_id=company_a.id,
        payload=UserCreate(
            name="Usuario Acme",
            email="user@acme.example.com",
            password="super-secret-4",
            role="agent",
        ),
    )

    with pytest.raises(HTTPException) as exc:
        get_user(db, company_id=company_b.id, user_id=user.id)
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        update_user(
            db,
            company_id=company_b.id,
            user_id=user.id,
            payload=UserUpdate(name="Otro nombre"),
        )
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        reset_user_password(
            db,
            company_id=company_b.id,
            user_id=user.id,
            payload=UserPasswordReset(password="another-secret"),
        )
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        deactivate_user(db, company_id=company_b.id, user_id=user.id)
    assert exc.value.status_code == 404


def test_restricted_routes_return_403_without_module_permission(db, client):
    company, owner = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente Acme",
            email="agent-route@acme.example.com",
            password="super-secret-5",
            role="agent",
        ),
    )

    token = build_token(agent)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403

    response = client.get("/api/v1/ai/agents", headers=headers)
    assert response.status_code == 403

    response = client.get("/api/v1/ai/prompts/default-system-prompt", headers=headers)
    assert response.status_code == 403

    owner_token = build_token(owner)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    response = client.get("/api/v1/users", headers=owner_headers)
    assert response.status_code == 200


def test_tenant_users_lookup_is_available_to_authenticated_tenant_members(db, client):
    company, owner = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente Acme",
            email="agent-tenant@acme.example.com",
            password="super-secret-6",
            role="agent",
        ),
    )
    other_company, _ = bootstrap_company(db, "Other")
    create_user(
        db,
        company_id=other_company.id,
        payload=UserCreate(
            name="Otro agente",
            email="other-agent@other.example.com",
            password="super-secret-7",
            role="agent",
        ),
    )

    headers = {"Authorization": f"Bearer {build_token(agent)}"}
    response = client.get("/api/v1/users/tenant", headers=headers)

    assert response.status_code == 200
    assert {user["id"] for user in response.json()} == {str(owner.id), str(agent.id)}
    assert all(user["company_id"] == str(company.id) for user in response.json())


def test_conversation_ai_controls_require_inbox_module_permission(db, client):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente sin inbox",
            email="agent-no-inbox@acme.example.com",
            password="super-secret-7",
            role="agent",
            module_permissions={"inbox": False},
        ),
    )

    headers = {"Authorization": f"Bearer {build_token(agent)}"}

    response = client.post(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000/ai/pause",
        headers=headers,
    )
    assert response.status_code == 403

    response = client.post(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000/ai/resume",
        headers=headers,
    )
    assert response.status_code == 403

    response = client.post(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000/assign",
        headers=headers,
        json={"assigned_user_id": str(agent.id)},
    )
    assert response.status_code == 403


def test_conversation_take_chat_blocks_stealing_an_assigned_thread(db, client):
    company, owner = bootstrap_company(db, "Acme")
    update_company(
        db,
        company_id=company.id,
        current_company_id=company.id,
        payload=CompanyUpdate(auto_assign_single_additional_user_chats=False),
        actor_user=owner,
    )
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente con inbox",
            email="agent-take@acme.example.com",
            password="super-secret-8",
            role="agent",
            module_permissions={"inbox": True},
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
    assert conversation.assigned_user_id is None
    assign_conversation(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        assigned_user_id=owner.id,
        actor_user=owner,
    )
    db.refresh(conversation)
    assert conversation.assigned_user_id == owner.id

    headers = {"Authorization": f"Bearer {build_token(agent)}"}
    response = client.post(
        f"/api/v1/conversations/{conversation.id}/assign",
        headers=headers,
        json={"assigned_user_id": str(agent.id)},
    )
    assert response.status_code == 403

    db.refresh(conversation)
    assert conversation.assigned_user_id == owner.id


def test_privileged_take_chat_can_overwrite_another_user_assignment(db):
    company, owner = bootstrap_company(db, "Acme")
    admin = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Admin con inbox",
            email="admin-take@acme.example.com",
            password="super-secret-12",
            role="agent",
            module_permissions={"inbox": True},
        ),
    )
    admin.role = "admin"
    db.commit()
    contact = Contact(company_id=company.id, name="Cliente", phone="+573001112234")
    db.add(contact)
    db.commit()
    conversation = create_conversation(
        db,
        company_id=company.id,
        payload=ConversationCreate(contact_id=contact.id, channel="whatsapp"),
    )
    assign_conversation(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        assigned_user_id=owner.id,
        actor_user=owner,
    )
    db.refresh(conversation)
    assert conversation.assigned_user_id == owner.id

    reassigned = assign_conversation(
        db,
        company_id=company.id,
        conversation_id=conversation.id,
        assigned_user_id=admin.id,
        actor_user=admin,
    )
    assert reassigned.assigned_user_id == admin.id

    db.refresh(conversation)
    assert conversation.assigned_user_id == admin.id


def test_company_auto_assign_toggle_requires_owner_or_admin(db, client):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente con settings",
            email="agent-autoassign@acme.example.com",
            password="super-secret-8",
            role="agent",
            module_permissions={"settings": True},
        ),
    )

    headers = {"Authorization": f"Bearer {build_token(agent)}"}

    response = client.put(
        f"/api/v1/companies/{company.id}",
        headers=headers,
        json={
            "auto_assign_single_additional_user_chats": False,
        },
    )
    assert response.status_code == 403


def test_users_routes_require_owner_or_admin_even_with_settings_permission(db, client):
    company, _ = bootstrap_company(db, "Acme")
    agent = create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente con settings",
            email="agent-settings@acme.example.com",
            password="super-secret-6",
            role="agent",
            module_permissions={"settings": True},
        ),
    )

    headers = {"Authorization": f"Bearer {build_token(agent)}"}

    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403

    response = client.get(f"/api/v1/users/{agent.id}", headers=headers)
    assert response.status_code == 403


def test_company_bootstrap_route_requires_superadmin(db, client):
    _, owner = bootstrap_company(db, "Acme")
    headers = {"Authorization": f"Bearer {build_token(owner)}"}

    response = client.post(
        "/api/v1/companies",
        headers=headers,
        json={
            "name": "Nueva Empresa",
            "owner": {
                "name": "Nuevo Owner",
                "email": "new-owner@example.com",
                "password": "super-secret-7",
            },
        },
    )

    assert response.status_code == 403


def test_audit_logs_route_returns_tenant_logs(db, client):
    company, owner = bootstrap_company(db, "Acme")
    create_user(
        db,
        company_id=company.id,
        payload=UserCreate(
            name="Agente Acme",
            email="agent-audit@acme.example.com",
            password="super-secret-8",
            role="agent",
        ),
        actor_user=owner,
    )

    headers = {"Authorization": f"Bearer {build_token(owner)}"}
    response = client.get("/api/v1/audit/logs", headers=headers)

    assert response.status_code == 200
    actions = {item["action"] for item in response.json()}
    assert "company.created" in actions
    assert "user.created" in actions

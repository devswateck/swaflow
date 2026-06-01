from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.auth.schemas import PasswordChangeRequest
from app.auth.service import authenticate_user, change_own_password
from app.ai.schemas import AiInteractiveTemplateCreate, AiInteractiveTemplateOption
from app.ai.service import create_interactive_template, list_interactive_templates
from app.companies.schemas import CompanyCreate
from app.companies.service import create_company_with_owner
from app.contacts.models import Contact
from app.core.schemas import OwnerCreate
from app.ai.runtime import (
    AutoReplyResult,
    _build_catalog_context,
    _infer_interactive_action,
    _selected_interactive_source_action,
)
from app.conversations.models import Conversation
from app.inventory.models import Inventory
from app.inventory.service import list_inventory
from app.messages.models import Message
from app.orders.schemas import OrderCreate, OrderItemCreate
from app.orders.service import create_order, generate_payment_link, mark_paid_by_reference
from app.products.models import Product
from app.products.service import get_product
from app.core.security import verify_password
from app.users.models import User
from app.users.service import get_user
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.service import (
    _incoming_message_content,
    _resolve_configured_action,
    _should_generate_auto_reply,
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
    assert owner.company_id == company.id
    assert owner.role == "owner"
    assert owner.email == "owner@acme.example.com"
    assert owner.password_hash != "super-secret"
    assert verify_password("super-secret", owner.password_hash)


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
        sku="TOP-250",
        price=Decimal("130000.00"),
        currency="COP",
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
    assert "Stock real disponible: 4" in context
    assert "stock: 6, reservado: 2" in context


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

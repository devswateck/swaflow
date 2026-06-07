from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

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
        _meta_request("POST", "/messages", access_token="token")

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

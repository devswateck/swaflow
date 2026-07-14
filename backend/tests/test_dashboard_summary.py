from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import inspect

from app.ai.schemas import AiAgentCreate
from app.ai.service import create_agent
from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentCreate, AppointmentOperationalConfigUpdate, AppointmentUpdate
from app.appointments.service import (
    create_appointment,
    get_shared_operational_config,
    update_appointment,
    update_shared_operational_config,
)
from app.auth.service import build_token
from app.companies.schemas import CompanyCreate
from app.companies.service import create_company_with_owner
from app.contacts.models import Contact
from app.conversations.models import Conversation
from app.core.schemas import OwnerCreate
from app.funnels.models import SalesFunnel, SalesFunnelStep
from app.messages.models import Message
from app.orders.models import Order
from app.orders.models import OrderItem
from app.products.models import Product
from app.users.models import User


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {build_token(user)}"}


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


def test_dashboard_summary_is_tenant_scoped_and_honest(db, client):
    company, owner = bootstrap_company(db, "Acme")
    other_company, _ = bootstrap_company(db, "Bravo")
    empty_company, empty_owner = bootstrap_company(db, "Delta")

    acme_contact = Contact(company_id=company.id, name="Cliente Acme", phone="+573001112233")
    bravo_contact = Contact(company_id=other_company.id, name="Cliente Bravo", phone="+573001112234")
    db.add_all([acme_contact, bravo_contact])
    db.flush()

    db.add_all(
        [
            Conversation(company_id=company.id, contact_id=acme_contact.id, unread_count=2),
            Conversation(company_id=company.id, contact_id=acme_contact.id, unread_count=3),
            Conversation(company_id=other_company.id, contact_id=bravo_contact.id, unread_count=7),
        ]
    )
    db.add_all(
        [
            Order(
                company_id=company.id,
                contact_id=acme_contact.id,
                status="paid",
                total=Decimal("120.50"),
                currency="COP",
                payment_status="paid",
                idempotency_key="acme-paid-1",
                metadata_json={},
            ),
            Order(
                company_id=other_company.id,
                contact_id=bravo_contact.id,
                status="paid",
                total=Decimal("999.99"),
                currency="COP",
                payment_status="paid",
                idempotency_key="bravo-paid-1",
                metadata_json={},
            ),
        ]
    )
    db.add_all(
        [
            Appointment(
                company_id=company.id,
                contact_id=acme_contact.id,
                scheduled_at=datetime(2026, 7, 12, 15, 0, tzinfo=UTC),
                duration_minutes=60,
                status="scheduled",
            ),
            Appointment(
                company_id=company.id,
                contact_id=acme_contact.id,
                scheduled_at=datetime(2026, 7, 12, 16, 0, tzinfo=UTC),
                duration_minutes=45,
                status="completed",
            ),
            Appointment(
                company_id=other_company.id,
                contact_id=bravo_contact.id,
                scheduled_at=datetime(2026, 7, 12, 17, 0, tzinfo=UTC),
                duration_minutes=30,
                status="scheduled",
            ),
        ]
    )
    db.commit()

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers(owner))
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_conversations"] == 2
    assert summary["total_unread"] == 5
    assert Decimal(str(summary["confirmed_sales_total"])) == Decimal("120.50")
    assert summary["appointments_total"] == 2

    empty_response = client.get("/api/v1/dashboard/summary", headers=auth_headers(empty_owner))
    assert empty_response.status_code == 200
    empty_summary = empty_response.json()
    assert empty_summary["total_conversations"] == 0
    assert empty_summary["total_unread"] == 0
    assert Decimal(str(empty_summary["confirmed_sales_total"])) == Decimal("0")
    assert empty_summary["appointments_total"] == 0


def test_dashboard_product_filter_has_supporting_order_item_index(db):
    indexes = inspect(db.get_bind()).get_indexes("order_items")
    index_names = {index["name"] for index in indexes}

    assert "ix_order_items_company_product_order_id" in index_names
    assert "ix_orders_company_conversation_id" in {index["name"] for index in inspect(db.get_bind()).get_indexes("orders")}
    assert "ix_appointments_company_conversation_id" in {
        index["name"] for index in inspect(db.get_bind()).get_indexes("appointments")
    }
    assert "ix_conversations_company_assigned_user_status" in {
        index["name"] for index in inspect(db.get_bind()).get_indexes("conversations")
    }


def test_dashboard_rejects_invalid_company_timezone(db, client):
    company, owner = bootstrap_company(db, "Timezone")
    company.timezone = "Mars/Phobos"
    db.commit()

    response = client.get(
        "/api/v1/dashboard/analytics",
        params={"date_from": "2026-07-10", "date_to": "2026-07-11"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    analytics = response.json()
    assert analytics["timezone"] == "UTC"


def test_update_appointment_rejects_null_datetime_fields(db):
    company, _ = bootstrap_company(db, "Sigma")
    contact = Contact(company_id=company.id, name="Cliente Sigma", phone="+573001112299")
    db.add(contact)
    db.flush()
    appointment = create_appointment(
        db,
        company_id=company.id,
        payload=AppointmentCreate(
            contact_id=contact.id,
            scheduled_at=datetime(2026, 7, 12, 10, 0, tzinfo=UTC),
            duration_minutes=60,
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        update_appointment(
            db,
            company_id=company.id,
            appointment_id=appointment.id,
            payload=AppointmentUpdate(scheduled_at=None),
        )

    assert exc_info.value.status_code == 422


def test_shared_operational_config_rejects_stale_version(db):
    company, _ = bootstrap_company(db, "Theta")
    create_agent(
        db,
        company_id=company.id,
        payload=AiAgentCreate(
            name="Agente Theta",
            system_prompt="Sistema",
            conversation_objective="Objetivo",
        ),
    )

    current = get_shared_operational_config(db, company_id=company.id)
    saved = update_shared_operational_config(
        db,
        company_id=company.id,
        payload=AppointmentOperationalConfigUpdate(
            status=current.status,
            version=current.version,
            published_at=current.published_at,
            draft=current.draft,
            published=current.published,
        ),
    )
    assert saved.version == current.version + 1

    with pytest.raises(HTTPException) as exc_info:
        update_shared_operational_config(
            db,
            company_id=company.id,
            payload=AppointmentOperationalConfigUpdate(
                status=current.status,
                version=current.version,
                published_at=current.published_at,
                draft=current.draft,
                published=current.published,
            ),
        )

    assert exc_info.value.status_code == 409


def test_dashboard_analytics_filters_are_tenant_scoped_and_historical(db, client):
    company, owner = bootstrap_company(db, "Alpha")
    other_company, other_owner = bootstrap_company(db, "Beta")

    contact = Contact(company_id=company.id, name="Cliente Alpha", phone="+573001112300")
    other_contact = Contact(company_id=other_company.id, name="Cliente Beta", phone="+573001112301")
    db.add_all([contact, other_contact])
    db.flush()

    funnel = SalesFunnel(
        company_id=company.id,
        name="Venta principal",
        system_key="principal",
        description="",
        status="active",
        is_default=True,
        welcome_message="Hola",
        capture_fields=["nombre"],
        assignment_criteria="",
    )
    funnel_step = SalesFunnelStep(
        company_id=company.id,
        funnel=funnel,
        position=1,
        name="Prospeccion",
        code="prospeccion",
        prompt="",
        objectives=[],
        transition_criteria="",
        status="active",
        config={},
    )
    product = Product(
        company_id=company.id,
        name="Plan Pro",
        description="",
        sku="PRO-001",
        price=Decimal("120.50"),
        currency="COP",
        status="active",
        whatsapp_catalog_id="catalog-1",
        whatsapp_product_retailer_id="retailer-1",
        metadata_json={},
    )
    other_product = Product(
        company_id=other_company.id,
        name="Plan Beta",
        description="",
        sku="BETA-001",
        price=Decimal("999.99"),
        currency="COP",
        status="active",
        whatsapp_catalog_id="catalog-2",
        whatsapp_product_retailer_id="retailer-2",
        metadata_json={},
    )
    db.add_all([funnel, funnel_step, product, other_product])
    db.flush()

    alpha_conversation = Conversation(
        company_id=company.id,
        contact_id=contact.id,
        assigned_user_id=owner.id,
        status="open",
        funnel_id=funnel.id,
        funnel_step_id=funnel_step.id,
        current_step="Prospeccion",
        unread_count=4,
        last_message_at=datetime(2026, 7, 10, 12, 30, tzinfo=UTC),
    )
    alpha_created_only_conversation = Conversation(
        company_id=company.id,
        contact_id=contact.id,
        assigned_user_id=owner.id,
        status="open",
        funnel_id=funnel.id,
        funnel_step_id=funnel_step.id,
        current_step=None,
        unread_count=3,
        created_at=datetime(2026, 7, 11, 9, 15, tzinfo=UTC),
        last_message_at=None,
    )
    alpha_old_product_conversation = Conversation(
        company_id=company.id,
        contact_id=contact.id,
        assigned_user_id=owner.id,
        status="open",
        funnel_id=funnel.id,
        funnel_step_id=funnel_step.id,
        current_step=None,
        unread_count=2,
        created_at=datetime(2026, 7, 10, 8, 15, tzinfo=UTC),
        last_message_at=datetime(2026, 7, 10, 9, 15, tzinfo=UTC),
    )
    beta_conversation = Conversation(
        company_id=other_company.id,
        contact_id=other_contact.id,
        assigned_user_id=other_owner.id,
        status="open",
        funnel_id=None,
        funnel_step_id=None,
        current_step=None,
        unread_count=11,
        last_message_at=datetime(2026, 7, 10, 13, 0, tzinfo=UTC),
    )
    db.add_all([
        alpha_conversation,
        alpha_created_only_conversation,
        alpha_old_product_conversation,
        beta_conversation,
    ])
    db.flush()

    db.add_all(
        [
            Message(
                company_id=company.id,
                conversation_id=alpha_conversation.id,
                external_message_id="msg-1",
                sender_type="customer",
                content="Hola",
                message_type="text",
                metadata_json={},
                created_at=datetime(2026, 7, 10, 11, 0, tzinfo=UTC),
            ),
            Message(
                company_id=company.id,
                conversation_id=alpha_conversation.id,
                external_message_id="msg-2",
                sender_type="agent",
                content="Te ayudo",
                message_type="text",
                metadata_json={},
                created_at=datetime(2026, 7, 10, 11, 10, tzinfo=UTC),
            ),
            Message(
                company_id=other_company.id,
                conversation_id=beta_conversation.id,
                external_message_id="msg-3",
                sender_type="customer",
                content="Hola Beta",
                message_type="text",
                metadata_json={},
                created_at=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
            ),
        ]
    )
    order = Order(
        company_id=company.id,
        contact_id=contact.id,
        conversation_id=alpha_conversation.id,
        status="paid",
        total=Decimal("120.50"),
        currency="COP",
        payment_status="paid",
        idempotency_key="alpha-order-1",
        metadata_json={},
        created_at=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
    )
    other_order = Order(
        company_id=other_company.id,
        contact_id=other_contact.id,
        conversation_id=beta_conversation.id,
        status="paid",
        total=Decimal("999.99"),
        currency="COP",
        payment_status="paid",
        idempotency_key="beta-order-1",
        metadata_json={},
        created_at=datetime(2026, 7, 10, 12, 30, tzinfo=UTC),
    )
    created_only_order = Order(
        company_id=company.id,
        contact_id=contact.id,
        conversation_id=alpha_created_only_conversation.id,
        status="paid",
        total=Decimal("55.00"),
        currency="COP",
        payment_status="paid",
        idempotency_key="alpha-order-2",
        metadata_json={},
        created_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
    )
    old_product_order = Order(
        company_id=company.id,
        contact_id=contact.id,
        conversation_id=alpha_old_product_conversation.id,
        status="paid",
        total=Decimal("80.00"),
        currency="COP",
        payment_status="paid",
        idempotency_key="alpha-order-3",
        metadata_json={},
        created_at=datetime(2026, 7, 9, 10, 0, tzinfo=UTC),
    )
    db.add_all([order, other_order, created_only_order, old_product_order])
    db.flush()
    db.add_all(
        [
            OrderItem(
                company_id=company.id,
                order_id=order.id,
                product_id=product.id,
                quantity=1,
                unit_price=Decimal("120.50"),
                total=Decimal("120.50"),
            ),
            OrderItem(
                company_id=other_company.id,
                order_id=other_order.id,
                product_id=other_product.id,
                quantity=1,
                unit_price=Decimal("999.99"),
                total=Decimal("999.99"),
            ),
            OrderItem(
                company_id=company.id,
                order_id=created_only_order.id,
                product_id=product.id,
                quantity=1,
                unit_price=Decimal("55.00"),
                total=Decimal("55.00"),
            ),
            OrderItem(
                company_id=company.id,
                order_id=old_product_order.id,
                product_id=product.id,
                quantity=1,
                unit_price=Decimal("80.00"),
                total=Decimal("80.00"),
            ),
        ]
    )
    db.add_all(
        [
            Appointment(
                company_id=company.id,
                contact_id=contact.id,
                conversation_id=alpha_conversation.id,
                assigned_user_id=owner.id,
                scheduled_at=datetime(2026, 7, 10, 15, 0, tzinfo=UTC),
                duration_minutes=60,
                status="scheduled",
            ),
            Appointment(
                company_id=company.id,
                contact_id=contact.id,
                conversation_id=alpha_conversation.id,
                assigned_user_id=owner.id,
                scheduled_at=datetime(2026, 7, 11, 15, 0, tzinfo=UTC),
                duration_minutes=60,
                status="completed",
            ),
            Appointment(
                company_id=other_company.id,
                contact_id=other_contact.id,
                conversation_id=beta_conversation.id,
                assigned_user_id=other_owner.id,
                scheduled_at=datetime(2026, 7, 10, 15, 0, tzinfo=UTC),
                duration_minutes=60,
                status="scheduled",
            ),
        ]
    )
    db.commit()

    response = client.get(
        "/api/v1/dashboard/analytics",
        params={
            "date_from": "2026-07-10",
            "date_to": "2026-07-11",
            "assigned_user_id": str(owner.id),
            "status": "open",
            "funnel_id": str(funnel.id),
            "funnel_step_id": str(funnel_step.id),
            "product_id": str(product.id),
        },
        headers=auth_headers(owner),
    )
    assert response.status_code == 200
    analytics = response.json()
    assert analytics["date_from"] == "2026-07-10"
    assert analytics["date_to"] == "2026-07-11"
    assert analytics["timezone"] == "UTC"
    assert analytics["summary"]["total_conversations"] == 2
    assert analytics["summary"]["total_unread"] == 7
    assert Decimal(str(analytics["summary"]["confirmed_sales_total"])) == Decimal("175.50")
    assert analytics["summary"]["appointments_total"] == 2
    assert len(analytics["series"]) == 2
    first_day = analytics["series"][0]
    assert first_day["date"] == "2026-07-10"
    assert first_day["chats_received"] == 1
    assert first_day["chats_sent"] == 1
    assert first_day["orders_created"] == 1
    assert first_day["orders_paid"] == 1
    assert Decimal(str(first_day["orders_paid_total"])) == Decimal("120.50")
    assert first_day["appointments_scheduled"] == 1
    assert first_day["appointments_completed"] == 0
    assert first_day["appointments_cancelled"] == 0
    second_day = analytics["series"][1]
    assert second_day["date"] == "2026-07-11"
    assert second_day["chats_received"] == 0
    assert second_day["chats_sent"] == 0
    assert second_day["orders_created"] == 1
    assert second_day["orders_paid"] == 1
    assert Decimal(str(second_day["orders_paid_total"])) == Decimal("55.00")
    assert second_day["appointments_scheduled"] == 0
    assert second_day["appointments_completed"] == 1
    assert second_day["appointments_cancelled"] == 0

    other_response = client.get(
        "/api/v1/dashboard/analytics",
        params={
            "date_from": "2026-07-10",
            "date_to": "2026-07-11",
            "assigned_user_id": str(other_owner.id),
            "status": "open",
            "funnel_id": str(funnel.id),
            "funnel_step_id": str(funnel_step.id),
            "product_id": str(product.id),
        },
        headers=auth_headers(other_owner),
    )
    assert other_response.status_code == 200
    other_analytics = other_response.json()
    assert other_analytics["summary"]["total_conversations"] == 0
    assert other_analytics["summary"]["total_unread"] == 0
    assert Decimal(str(other_analytics["summary"]["confirmed_sales_total"])) == Decimal("0")
    assert other_analytics["summary"]["appointments_total"] == 0

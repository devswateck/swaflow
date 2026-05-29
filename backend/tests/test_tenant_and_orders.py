from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.auth.schemas import PasswordChangeRequest
from app.auth.service import authenticate_user, change_own_password
from app.companies.schemas import CompanyCreate
from app.companies.service import create_company_with_owner
from app.contacts.models import Contact
from app.core.schemas import OwnerCreate
from app.inventory.models import Inventory
from app.orders.schemas import OrderCreate, OrderItemCreate
from app.orders.service import create_order, generate_payment_link, mark_paid_by_reference
from app.products.models import Product
from app.products.service import get_product
from app.core.security import verify_password
from app.users.models import User
from app.users.service import get_user


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

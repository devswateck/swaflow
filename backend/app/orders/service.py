from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.contacts.service import get_contact
from app.conversations.service import get_conversation
from app.events.service import create_event
from app.inventory.models import Inventory
from app.inventory.service import available_units, get_inventory_by_product
from app.orders.models import Order, OrderItem
from app.orders.schemas import OrderCreate
from app.products.models import Product
from app.products.service import get_product


def list_orders(db: Session, *, company_id: UUID, limit: int, offset: int) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.company_id == company_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


def get_order(db: Session, *, company_id: UUID, order_id: UUID) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.company_id == company_id, Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def _load_product_for_order(db: Session, *, company_id: UUID, product_id: UUID) -> Product:
    product = get_product(db, company_id=company_id, product_id=product_id)
    if product.status != "active":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Inactive product")
    return product


def create_order(db: Session, *, company_id: UUID, payload: OrderCreate) -> Order:
    get_contact(db, company_id=company_id, contact_id=payload.contact_id)
    if payload.conversation_id is not None:
        get_conversation(db, company_id=company_id, conversation_id=payload.conversation_id)

    order = Order(
        company_id=company_id,
        contact_id=payload.contact_id,
        conversation_id=payload.conversation_id,
        status="pending",
        payment_status="pending",
        currency="COP",
        metadata_json=payload.metadata,
    )
    db.add(order)
    db.flush()

    total = Decimal("0")
    currency: str | None = None
    touched_inventory: list[tuple[Inventory, int]] = []

    try:
        for requested_item in payload.items:
            product = _load_product_for_order(
                db, company_id=company_id, product_id=requested_item.product_id
            )
            inventory = get_inventory_by_product(
                db, company_id=company_id, product_id=requested_item.product_id
            )
            if available_units(inventory) < requested_item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient stock for product {product.id}",
                )

            if currency is None:
                currency = product.currency
            elif currency != product.currency:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="All order items must use the same currency",
                )

            item_total = product.price * requested_item.quantity
            total += item_total
            inventory.quantity_reserved += requested_item.quantity
            touched_inventory.append((inventory, requested_item.quantity))
            db.add(
                OrderItem(
                    company_id=company_id,
                    order_id=order.id,
                    product_id=product.id,
                    quantity=requested_item.quantity,
                    unit_price=product.price,
                    total=item_total,
                )
            )
    except Exception:
        for inventory, quantity in touched_inventory:
            inventory.quantity_reserved -= quantity
        raise

    order.total = total
    order.currency = currency or "COP"
    create_event(
        db,
        company_id=company_id,
        event_type="order.created",
        payload={"order_id": str(order.id), "total": str(order.total), "currency": order.currency},
    )
    db.commit()
    db.refresh(order)
    return get_order(db, company_id=company_id, order_id=order.id)


def generate_payment_link(db: Session, *, company_id: UUID, order_id: UUID) -> Order:
    order = get_order(db, company_id=company_id, order_id=order_id)
    if order.status not in {"pending", "waiting_payment"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payment link can only be generated for pending orders",
        )
    reference = order.payment_reference or f"mock_{uuid4().hex}"
    order.payment_provider = "mock"
    order.payment_reference = reference
    order.payment_link = f"https://payments.example.test/pay/{reference}"
    order.status = "waiting_payment"
    order.payment_status = "pending"
    create_event(
        db,
        company_id=company_id,
        event_type="order.waiting_payment",
        payload={"order_id": str(order.id), "payment_reference": reference},
    )
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, *, company_id: UUID, order_id: UUID) -> Order:
    order = get_order(db, company_id=company_id, order_id=order_id)
    if order.status in {"paid", "processing", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order cannot be cancelled from its current status",
        )
    for item in order.items:
        inventory = get_inventory_by_product(db, company_id=company_id, product_id=item.product_id)
        inventory.quantity_reserved = max(0, inventory.quantity_reserved - item.quantity)
    order.status = "cancelled"
    order.payment_status = "cancelled"
    create_event(
        db,
        company_id=company_id,
        event_type="order.cancelled",
        payload={"order_id": str(order.id)},
    )
    db.commit()
    db.refresh(order)
    return order


def mark_paid_by_reference(db: Session, *, payment_reference: str, provider: str = "mock") -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.payment_reference == payment_reference, Order.payment_provider == provider)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status == "paid":
        return order
    if order.status not in {"waiting_payment", "pending"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order cannot be marked as paid from its current status",
        )

    for item in order.items:
        inventory = get_inventory_by_product(
            db, company_id=order.company_id, product_id=item.product_id
        )
        if inventory.quantity_available < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient stock to settle paid order",
            )
        inventory.quantity_available -= item.quantity
        inventory.quantity_reserved = max(0, inventory.quantity_reserved - item.quantity)

    order.status = "paid"
    order.payment_status = "paid"
    create_event(
        db,
        company_id=order.company_id,
        event_type="order.paid",
        payload={"order_id": str(order.id), "payment_reference": payment_reference},
    )
    db.commit()
    db.refresh(order)
    return order


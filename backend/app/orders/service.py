from decimal import Decimal
import logging
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.crypto import decrypt_secret
from app.contacts.service import get_contact
from app.conversations.service import get_conversation
from app.events.service import create_event
from app.inventory.models import Inventory
from app.inventory.service import available_units, get_inventory_by_product
from app.integrations.models import CompanyIntegration
from app.orders.models import Order, OrderItem
from app.orders.schemas import OrderCreate
from app.payments.notifications import notify_order_paid
from app.payments.providers.wompi import create_payment_link as create_wompi_payment_link
from app.payments.providers.wompi import parse_credentials as parse_wompi_credentials
from app.products.models import Product
from app.products.service import get_product

logger = logging.getLogger(__name__)


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


def _get_payment_integration(db: Session, *, company_id: UUID) -> CompanyIntegration | None:
    return db.scalar(
        select(CompanyIntegration)
        .where(
            CompanyIntegration.company_id == company_id,
            CompanyIntegration.type == "payments",
            CompanyIntegration.status == "active",
        )
        .order_by(CompanyIntegration.updated_at.desc())
    )


def _payment_link_ttl_minutes(config: dict) -> int:
    try:
        return int(config.get("payment_link_ttl_minutes") or 120)
    except (TypeError, ValueError):
        return 120


def generate_payment_link(db: Session, *, company_id: UUID, order_id: UUID) -> Order:
    order = get_order(db, company_id=company_id, order_id=order_id)
    if order.status not in {"pending", "waiting_payment"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payment link can only be generated for pending orders",
        )

    reference = order.payment_reference or f"swaflow_{uuid4().hex[:28]}"
    integration = _get_payment_integration(db, company_id=company_id)
    provider = (
        str((integration.config or {}).get("provider") or "mock").lower()
        if integration is not None
        else "mock"
    )

    if provider == "wompi" and integration is not None and integration.credentials_encrypted:
        config = integration.config if isinstance(integration.config, dict) else {}
        credentials = parse_wompi_credentials(decrypt_secret(integration.credentials_encrypted))
        link = create_wompi_payment_link(
            credentials=credentials,
            environment=str(config.get("environment") or "sandbox"),
            order_id=str(order.id),
            reference=reference,
            amount=order.total,
            currency=order.currency,
            redirect_url=str(config.get("redirect_url") or "").strip() or None,
            expires_in_minutes=_payment_link_ttl_minutes(config),
        )
        order.payment_provider = "wompi"
        order.payment_reference = link.reference
        order.payment_link = link.url
        metadata = order.metadata_json if isinstance(order.metadata_json, dict) else {}
        metadata["payment"] = {
            "provider": "wompi",
            "link_id": link.link_id,
            "expires_at": link.expires_at.isoformat(),
        }
        order.metadata_json = metadata
    else:
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


def _mark_order_paid(db: Session, *, order: Order) -> Order:
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
        payload={"order_id": str(order.id), "payment_reference": order.payment_reference},
    )
    db.commit()
    db.refresh(order)
    try:
        notify_order_paid(db, order=order)
    except Exception:
        logger.exception("Failed to send payment notifications for order_id=%s", order.id)
    return order


def mark_paid_by_reference(db: Session, *, payment_reference: str, provider: str = "mock") -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.payment_reference == payment_reference, Order.payment_provider == provider)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return _mark_order_paid(db, order=order)


def update_payment_status(db: Session, *, order: Order, payment_status: str) -> Order:
    normalized = payment_status.strip().lower()
    if normalized in {"approved", "paid"}:
        return _mark_order_paid(db, order=order)

    if normalized in {"declined", "voided", "error", "failed"}:
        order.payment_status = "failed"
    elif normalized in {"expired"}:
        order.payment_status = "expired"
    else:
        order.payment_status = normalized or "pending"

    create_event(
        db,
        company_id=order.company_id,
        event_type="order.payment_status",
        payload={
            "order_id": str(order.id),
            "payment_reference": order.payment_reference,
            "payment_status": order.payment_status,
        },
    )
    db.commit()
    db.refresh(order)
    return order


def update_payment_status_by_reference(
    db: Session, *, payment_reference: str, provider: str, payment_status: str
) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.payment_reference == payment_reference, Order.payment_provider == provider)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return update_payment_status(db, order=order, payment_status=payment_status)

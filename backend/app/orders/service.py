from decimal import Decimal
from datetime import UTC, date, datetime, time, timedelta
import logging
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import exists, select
from sqlalchemy.orm import Session, selectinload

from app.companies.models import Company
from app.contacts.service import get_contact
from app.audit.service import record_audit_best_effort
from app.conversations.models import Conversation
from app.conversations.service import get_conversation
from app.events.service import create_event
from app.inventory.models import Inventory
from app.inventory.service import available_units, get_inventory_by_product
from app.integrations.models import CompanyIntegration
from app.orders.models import Order, OrderItem
from app.orders.schemas import OrderCreate
from app.payments.contract import (
    get_payment_adapter,
    normalize_payment_provider,
    payment_credentials_raw,
    validate_payment_integration_config,
)
from app.payments.notifications import notify_order_paid
from app.products.models import Product
from app.products.service import get_product, is_meta_synced_product
from app.realtime import realtime_manager
from app.whatsapp.service import send_expired_payment_followup

logger = logging.getLogger(__name__)
ACTIVE_CONVERSATION_STATUSES = {"open", "waiting_customer", "waiting_human"}


def _tenant_timezone(db: Session, *, company_id: UUID) -> ZoneInfo:
    company = db.scalar(select(Company).where(Company.id == company_id))
    timezone_name = company.timezone if company is not None else None
    try:
        return ZoneInfo(timezone_name or "UTC")
    except Exception:
        logger.warning(
            "Invalid company timezone, falling back to UTC",
            extra={"company_id": str(company_id), "timezone": timezone_name},
        )
        return ZoneInfo("UTC")


def _day_start(value: date, *, timezone: ZoneInfo) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone).astimezone(UTC)


def _day_end(value: date, *, timezone: ZoneInfo) -> datetime:
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone).astimezone(UTC)


def list_orders(
    db: Session,
    *,
    company_id: UUID,
    limit: int,
    offset: int,
    created_from: date | None = None,
    created_to: date | None = None,
    status_filter: str | None = None,
    payment_status_filter: str | None = None,
    contact_id: UUID | None = None,
    conversation_id: UUID | None = None,
    product_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
) -> list[Order]:
    stmt = select(Order).options(selectinload(Order.items)).where(Order.company_id == company_id)
    tenant_timezone = _tenant_timezone(db, company_id=company_id)

    if created_from is not None:
        stmt = stmt.where(Order.created_at >= _day_start(created_from, timezone=tenant_timezone))
    if created_to is not None:
        stmt = stmt.where(Order.created_at < _day_end(created_to, timezone=tenant_timezone))
    if status_filter:
        stmt = stmt.where(Order.status == status_filter.strip().lower())
    if payment_status_filter:
        stmt = stmt.where(Order.payment_status == payment_status_filter.strip().lower())
    if contact_id is not None:
        stmt = stmt.where(Order.contact_id == contact_id)
    if conversation_id is not None:
        stmt = stmt.where(Order.conversation_id == conversation_id)
    if product_id is not None:
        stmt = stmt.where(
            exists(
                select(1).select_from(OrderItem).where(
                    OrderItem.company_id == company_id,
                    OrderItem.order_id == Order.id,
                    OrderItem.product_id == product_id,
                )
            )
        )
    if assigned_user_id is not None:
        stmt = stmt.where(
            exists(
                select(1).select_from(Conversation).where(
                    Conversation.company_id == company_id,
                    Conversation.id == Order.conversation_id,
                    Conversation.assigned_user_id == assigned_user_id,
                )
            )
        )

    return list(
        db.scalars(
            stmt.order_by(Order.created_at.desc())
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
    if not is_meta_synced_product(product):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Product must be synchronized from Meta",
        )
    return product


def _extract_idempotency_key(payload: OrderCreate) -> str | None:
    raw_key = payload.metadata.get("idempotency_key")
    if not isinstance(raw_key, str):
        return None
    normalized = raw_key.strip()
    return normalized or None


def _order_matches_payload(order: Order, payload: OrderCreate) -> bool:
    if order.contact_id != payload.contact_id or order.conversation_id != payload.conversation_id:
        return False
    if len(order.items) != len(payload.items):
        return False
    ordered_items = sorted(
        ((item.product_id, item.quantity) for item in order.items),
        key=lambda item: (str(item[0]), item[1]),
    )
    requested_items = sorted(
        ((item.product_id, item.quantity) for item in payload.items),
        key=lambda item: (str(item[0]), item[1]),
    )
    return ordered_items == requested_items


def _find_idempotent_order(db: Session, *, company_id: UUID, idempotency_key: str) -> Order | None:
    return db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.company_id == company_id, Order.idempotency_key == idempotency_key)
    )


def create_order(
    db: Session,
    *,
    company_id: UUID,
    payload: OrderCreate,
    actor_user=None,
) -> Order:
    get_contact(db, company_id=company_id, contact_id=payload.contact_id)
    explicit_idempotency_key = _extract_idempotency_key(payload)
    if explicit_idempotency_key is not None:
        existing_order = _find_idempotent_order(
            db,
            company_id=company_id,
            idempotency_key=explicit_idempotency_key,
        )
        if existing_order is not None:
            if not _order_matches_payload(existing_order, payload):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used for a different order payload",
                )
            return existing_order

    conversation = get_conversation(db, company_id=company_id, conversation_id=payload.conversation_id)
    if conversation.contact_id != payload.contact_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conversation does not belong to the supplied contact",
        )
    if conversation.status not in ACTIVE_CONVERSATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conversation must be active to create an order",
        )

    order = Order(
        company_id=company_id,
        contact_id=payload.contact_id,
        conversation_id=payload.conversation_id,
        status="pending",
        payment_status="pending",
        currency="COP",
        metadata_json=payload.metadata,
    )
    if explicit_idempotency_key is not None:
        order.idempotency_key = explicit_idempotency_key
    db.add(order)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if explicit_idempotency_key is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to create order",
            )
        existing_order = _find_idempotent_order(
            db,
            company_id=company_id,
            idempotency_key=explicit_idempotency_key,
        )
        if existing_order is not None:
            if not _order_matches_payload(existing_order, payload):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used for a different order payload",
                )
            return existing_order
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key already used for a different order payload",
        )

    total = Decimal("0")
    currency: str | None = None
    touched_inventory: list[tuple[Inventory, int]] = []

    try:
        for requested_item in payload.items:
            product = _load_product_for_order(
                db, company_id=company_id, product_id=requested_item.product_id
            )
            inventory = get_inventory_by_product(
                db, company_id=company_id, product_id=requested_item.product_id, for_update=True
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
        payload={
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
            "total": str(order.total),
            "currency": order.currency,
        },
    )
    db.commit()
    db.refresh(order)
    realtime_manager.publish(
        company_id,
        "order.created",
        {
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
        },
    )
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="order.created",
        entity_type="order",
        entity_id=order.id,
        summary="Order created",
        metadata={"total": str(order.total), "currency": order.currency},
    )
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


def generate_payment_link(
    db: Session,
    *,
    company_id: UUID,
    order_id: UUID,
    actor_user=None,
) -> Order:
    order = get_order(db, company_id=company_id, order_id=order_id)
    if order.status not in {"pending", "waiting_payment"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payment link can only be generated for pending orders",
        )

    integration = _get_payment_integration(db, company_id=company_id)
    if integration is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Active payment integration is required to generate a payment link",
        )

    config = integration.config if isinstance(integration.config, dict) else {}
    credentials_raw = payment_credentials_raw(integration)
    validate_payment_integration_config(
        config=config,
        credentials_raw=credentials_raw,
        integration_status=integration.status,
    )

    reference = order.payment_reference or f"swaflow_{uuid4().hex[:28]}"
    provider = normalize_payment_provider(config)
    adapter = get_payment_adapter(provider)
    link = adapter.create_payment_link(
        credentials_raw=credentials_raw,
        config=config,
        order_id=str(order.id),
        reference=reference,
        amount=order.total,
        currency=order.currency,
    )
    order.payment_provider = provider

    order.payment_reference = link.reference
    order.payment_link = link.url
    metadata = order.metadata_json if isinstance(order.metadata_json, dict) else {}
    payment_metadata = metadata.get("payment", {}) if isinstance(metadata.get("payment"), dict) else {}
    payment_metadata.update({
        "provider": order.payment_provider,
        "link_id": link.link_id,
        "expires_at": link.expires_at.isoformat(),
    })
    metadata["payment"] = payment_metadata
    order.metadata_json = metadata

    order.status = "waiting_payment"
    order.payment_status = "pending"
    create_event(
        db,
        company_id=company_id,
        event_type="order.waiting_payment",
        payload={
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
            "payment_reference": reference,
        },
    )
    db.commit()
    db.refresh(order)
    realtime_manager.publish(
        company_id,
        "order.waiting_payment",
        {
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
            "payment_reference": reference,
        },
    )
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="order.payment_link_generated",
        entity_type="order",
        entity_id=order.id,
        summary="Payment link generated",
        metadata={"payment_reference": reference, "provider": order.payment_provider},
    )
    return order


def cancel_order(
    db: Session,
    *,
    company_id: UUID,
    order_id: UUID,
    actor_user=None,
) -> Order:
    order = get_order(db, company_id=company_id, order_id=order_id)
    if order.status in {"paid", "processing", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order cannot be cancelled from its current status",
        )
    for item in order.items:
        inventory = get_inventory_by_product(
            db, company_id=company_id, product_id=item.product_id, for_update=True
        )
        inventory.quantity_reserved = max(0, inventory.quantity_reserved - item.quantity)
    order.status = "cancelled"
    order.payment_status = "cancelled"
    create_event(
        db,
        company_id=company_id,
        event_type="order.cancelled",
        payload={
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
        },
    )
    db.commit()
    db.refresh(order)
    realtime_manager.publish(
        company_id,
        "order.cancelled",
        {
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
        },
    )
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="order.cancelled",
        entity_type="order",
        entity_id=order.id,
        summary="Order cancelled",
    )
    return order


def _mark_order_paid(db: Session, *, order: Order, actor_user=None) -> Order:
    if order.status == "paid":
        return order
    if order.status not in {"waiting_payment", "pending"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Order cannot be marked as paid from its current status",
        )

    for item in order.items:
        inventory = get_inventory_by_product(
            db, company_id=order.company_id, product_id=item.product_id, for_update=True
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
        payload={
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
            "payment_reference": order.payment_reference,
        },
    )
    db.commit()
    db.refresh(order)
    realtime_manager.publish(
        order.company_id,
        "order.paid",
        {
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
            "payment_reference": order.payment_reference,
        },
    )
    record_audit_best_effort(
        db,
        company_id=order.company_id,
        actor_user=actor_user,
        action="order.paid",
        entity_type="order",
        entity_id=order.id,
        summary="Order marked as paid",
        metadata={"payment_reference": order.payment_reference, "payment_provider": order.payment_provider},
    )
    try:
        notify_order_paid(db, order=order)
    except Exception:
        logger.exception("Failed to send payment notifications for order_id=%s", order.id)
    return order


def mark_paid_by_reference(
    db: Session,
    *,
    payment_reference: str,
    provider: str = "mock",
    actor_user=None,
) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.payment_reference == payment_reference, Order.payment_provider == provider)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return _mark_order_paid(db, order=order, actor_user=actor_user)


def update_payment_status(db: Session, *, order: Order, payment_status: str, actor_user=None) -> Order:
    normalized = payment_status.strip().lower()
    if normalized in {"approved", "paid"}:
        return _mark_order_paid(db, order=order)

    if normalized in {"cancelled", "voided"}:
        for item in order.items:
            inventory = get_inventory_by_product(
                db, company_id=order.company_id, product_id=item.product_id, for_update=True
            )
            inventory.quantity_reserved = max(0, inventory.quantity_reserved - item.quantity)
        order.status = "cancelled"
        order.payment_status = "cancelled"
        create_event(
            db,
            company_id=order.company_id,
            event_type="order.cancelled",
            payload={
                "order_id": str(order.id),
                "conversation_id": str(order.conversation_id) if order.conversation_id else None,
                "payment_reference": order.payment_reference,
            },
        )
        db.commit()
        db.refresh(order)
        realtime_manager.publish(
            order.company_id,
            "order.cancelled",
            {
                "order_id": str(order.id),
                "conversation_id": str(order.conversation_id) if order.conversation_id else None,
                "payment_reference": order.payment_reference,
            },
        )
        record_audit_best_effort(
            db,
            company_id=order.company_id,
            actor_user=actor_user,
            action="order.cancelled",
            entity_type="order",
            entity_id=order.id,
            summary="Order cancelled via payment webhook",
            metadata={
                "payment_reference": order.payment_reference,
                "payment_status": order.payment_status,
            },
        )
        return order

    if normalized in {"declined", "error", "failed"}:
        order.payment_status = "failed"
    elif normalized in {"expired"}:
        for item in order.items:
            inventory = get_inventory_by_product(
                db, company_id=order.company_id, product_id=item.product_id, for_update=True
            )
            inventory.quantity_reserved = max(0, inventory.quantity_reserved - item.quantity)
        order.status = "expired"
        order.payment_status = "expired"
    else:
        order.payment_status = normalized or "pending"

    create_event(
        db,
        company_id=order.company_id,
        event_type="order.payment_status",
        payload={
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
            "payment_reference": order.payment_reference,
            "payment_status": order.payment_status,
        },
    )
    db.commit()
    db.refresh(order)
    if normalized == "expired":
        send_expired_payment_followup(db, order=order, actor_user=actor_user)
    realtime_manager.publish(
        order.company_id,
        "order.payment_status",
        {
            "order_id": str(order.id),
            "conversation_id": str(order.conversation_id) if order.conversation_id else None,
            "payment_reference": order.payment_reference,
            "payment_status": order.payment_status,
        },
    )
    record_audit_best_effort(
        db,
        company_id=order.company_id,
        actor_user=actor_user,
        action="order.payment_status_updated",
        entity_type="order",
        entity_id=order.id,
        summary="Payment status updated",
        metadata={
            "payment_reference": order.payment_reference,
            "payment_status": order.payment_status,
        },
    )
    return order


def update_payment_status_by_reference(
    db: Session,
    *,
    payment_reference: str,
    provider: str,
    payment_status: str,
    actor_user=None,
) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.payment_reference == payment_reference, Order.payment_provider == provider)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return update_payment_status(db, order=order, payment_status=payment_status, actor_user=actor_user)

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from datetime import date
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.core.database import get_db
from app.orders import service
from app.orders.models import Order
from app.orders.schemas import OrderCreate, OrderRead, PaymentLinkRead
from app.users.models import User

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderRead])
def list_orders(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    status: str | None = Query(default=None),
    payment_status: str | None = Query(default=None),
    contact_id: UUID | None = Query(default=None),
    conversation_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    assigned_user_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Order]:
    return service.list_orders(
        db,
        company_id=current_user.company_id,
        limit=limit,
        offset=offset,
        created_from=created_from,
        created_to=created_to,
        status_filter=status,
        payment_status_filter=payment_status,
        contact_id=contact_id,
        conversation_id=conversation_id,
        product_id=product_id,
        assigned_user_id=assigned_user_id,
    )


@router.post("", response_model=OrderRead, status_code=201)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    order = service.create_order(
        db,
        company_id=current_user.company_id,
        payload=payload,
        actor_user=current_user,
    )
    return order


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    return service.get_order(db, company_id=current_user.company_id, order_id=order_id)


@router.post("/{order_id}/payment-link", response_model=PaymentLinkRead)
def generate_payment_link(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentLinkRead:
    order = service.generate_payment_link(
        db,
        company_id=current_user.company_id,
        order_id=order_id,
        actor_user=current_user,
    )
    return PaymentLinkRead(
        payment_link=order.payment_link or "",
        payment_reference=order.payment_reference or "",
    )


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    order = service.cancel_order(
        db,
        company_id=current_user.company_id,
        order_id=order_id,
        actor_user=current_user,
    )
    return order

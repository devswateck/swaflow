from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.orders.service import mark_paid_by_reference
from app.payments.schemas import MockPaymentWebhook, PaymentWebhookResponse

router = APIRouter(prefix="/webhooks/payments", tags=["payments"])


@router.post("/wompi", response_model=PaymentWebhookResponse)
def wompi_webhook(payload: MockPaymentWebhook, db: Session = Depends(get_db)) -> PaymentWebhookResponse:
    if payload.status != "paid":
        return PaymentWebhookResponse(status="ignored")
    order = mark_paid_by_reference(
        db,
        payment_reference=payload.payment_reference,
        provider=payload.provider,
    )
    return PaymentWebhookResponse(status="processed", order_id=str(order.id))


@router.post("/mercado-pago", response_model=PaymentWebhookResponse)
def mercado_pago_webhook(
    payload: MockPaymentWebhook,
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    if payload.status != "paid":
        return PaymentWebhookResponse(status="ignored")
    if payload.provider not in {"mock", "mercado_pago"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid provider")
    order = mark_paid_by_reference(
        db,
        payment_reference=payload.payment_reference,
        provider=payload.provider,
    )
    return PaymentWebhookResponse(status="processed", order_id=str(order.id))


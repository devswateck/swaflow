from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.payments.service import process_payment_webhook
from app.payments.schemas import MockPaymentWebhook, PaymentWebhookResponse

router = APIRouter(prefix="/webhooks/payments", tags=["payments"])


@router.post("/wompi", response_model=PaymentWebhookResponse)
async def wompi_webhook(
    request: Request,
    x_event_checksum: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    payload = await request.json()
    return process_payment_webhook(
        db,
        provider="wompi",
        payload=payload,
        header_checksum=x_event_checksum,
    )


@router.post("/mercado-pago", response_model=PaymentWebhookResponse)
def mercado_pago_webhook(
    payload: MockPaymentWebhook,
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    if payload.status != "paid":
        return PaymentWebhookResponse(status="ignored")
    if payload.provider not in {"mock", "mercado_pago"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid provider")
    return process_payment_webhook(
        db,
        provider=payload.provider,
        payload=payload.model_dump(),
    )

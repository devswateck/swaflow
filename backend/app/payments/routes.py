from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.payments.service import process_payment_webhook
from app.payments.schemas import MockPaymentWebhook, PaymentWebhookPayload, PaymentWebhookResponse

router = APIRouter(prefix="/webhooks/payments", tags=["payments"])


@router.post("/wompi", response_model=PaymentWebhookResponse)
async def wompi_webhook(
    request: Request,
    x_event_checksum: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    raw_body = await request.body()
    payload = await request.json()
    return process_payment_webhook(
        db,
        provider="wompi",
        payload=payload,
        header_checksum=x_event_checksum,
        raw_body=raw_body,
    )


@router.post("/mock", response_model=PaymentWebhookResponse)
def mock_webhook(
    payload: MockPaymentWebhook,
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    if get_settings().app_env == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if payload.status != "paid":
        return PaymentWebhookResponse(status="ignored")
    if payload.provider != "mock":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid provider")
    return process_payment_webhook(
        db,
        provider=payload.provider,
        payload=payload.model_dump(),
    )


@router.post("/mercado-pago", response_model=PaymentWebhookResponse)
async def mercado_pago_webhook(
    request: Request,
    payload: PaymentWebhookPayload,
    x_swaflow_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    if payload.provider != "mercado_pago":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid provider")
    raw_body = await request.body()
    return process_payment_webhook(
        db,
        provider=payload.provider,
        payload=payload.model_dump(),
        header_checksum=x_swaflow_signature,
        raw_body=raw_body,
    )


@router.post("/aval-pay", response_model=PaymentWebhookResponse)
async def aval_pay_webhook(
    request: Request,
    payload: PaymentWebhookPayload,
    x_swaflow_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    if payload.provider != "aval_pay":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid provider")
    raw_body = await request.body()
    return process_payment_webhook(
        db,
        provider=payload.provider,
        payload=payload.model_dump(),
        header_checksum=x_swaflow_signature,
        raw_body=raw_body,
    )

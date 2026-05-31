from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret
from app.core.database import get_db
from app.integrations.models import CompanyIntegration
from app.orders.models import Order
from app.orders.service import mark_paid_by_reference, update_payment_status
from app.payments.schemas import MockPaymentWebhook, PaymentWebhookResponse
from app.payments.providers.wompi import (
    parse_credentials as parse_wompi_credentials,
    transaction_from_event,
    verify_event_checksum,
)

router = APIRouter(prefix="/webhooks/payments", tags=["payments"])


@router.post("/wompi", response_model=PaymentWebhookResponse)
async def wompi_webhook(
    request: Request,
    x_event_checksum: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    payload = await request.json()
    transaction = transaction_from_event(payload)
    payment_reference = str(transaction.get("reference") or transaction.get("sku") or "").strip()
    payment_link_id = str(transaction.get("payment_link_id") or "").strip()
    payment_status = str(transaction.get("status") or "").strip()
    if not payment_reference and not payment_link_id:
        return PaymentWebhookResponse(status="ignored")

    order = None
    if payment_reference:
        order = db.scalar(
            select(Order).where(
                Order.payment_reference == payment_reference,
                Order.payment_provider == "wompi",
            )
        )
    if order is None and payment_link_id:
        candidates = db.scalars(select(Order).where(Order.payment_provider == "wompi"))
        order = next(
            (
                candidate
                for candidate in candidates
                if str(
                    (
                        candidate.metadata_json.get("payment", {})
                        if isinstance(candidate.metadata_json, dict)
                        else {}
                    ).get("link_id")
                    or ""
                )
                == payment_link_id
            ),
            None,
        )
    if order is None:
        return PaymentWebhookResponse(status="ignored", payment_reference=payment_reference)

    integration = db.scalar(
        select(CompanyIntegration)
        .where(
            CompanyIntegration.company_id == order.company_id,
            CompanyIntegration.type == "payments",
            CompanyIntegration.status == "active",
        )
        .order_by(CompanyIntegration.updated_at.desc())
    )
    if integration and integration.credentials_encrypted:
        credentials = parse_wompi_credentials(decrypt_secret(integration.credentials_encrypted))
        if credentials.events_secret and not verify_event_checksum(
            payload,
            events_secret=credentials.events_secret,
            header_checksum=x_event_checksum,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Wompi event checksum",
            )

    metadata = dict(order.metadata_json) if isinstance(order.metadata_json, dict) else {}
    saved_payment_metadata = metadata.get("payment", {})
    payment_metadata = dict(saved_payment_metadata) if isinstance(saved_payment_metadata, dict) else {}
    payment_metadata["transaction_id"] = transaction.get("id")
    payment_metadata["transaction_reference"] = payment_reference or None
    metadata["payment"] = payment_metadata
    order.metadata_json = metadata
    order = update_payment_status(db, order=order, payment_status=payment_status)
    return PaymentWebhookResponse(
        status="processed",
        order_id=str(order.id),
        payment_reference=payment_reference,
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
    order = mark_paid_by_reference(
        db,
        payment_reference=payload.payment_reference,
        provider=payload.provider,
    )
    return PaymentWebhookResponse(status="processed", order_id=str(order.id))

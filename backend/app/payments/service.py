from __future__ import annotations

from sqlalchemy.orm import Session

from app.orders.service import update_payment_status
from app.payments.contract import (
    find_order_for_payment_event,
    get_active_payment_integration,
    get_payment_adapter,
    payment_credentials_raw,
    payment_event_already_processed,
    record_payment_transaction,
)
from app.payments.schemas import PaymentWebhookResponse


def process_payment_webhook(
    db: Session,
    *,
    provider: str,
    payload: dict,
    header_checksum: str | None = None,
) -> PaymentWebhookResponse:
    adapter = get_payment_adapter(provider)
    transaction = adapter.extract_transaction(payload)
    payment_reference = str(
        transaction.get("reference")
        or transaction.get("sku")
        or transaction.get("payment_reference")
        or ""
    ).strip()
    payment_link_id = str(transaction.get("payment_link_id") or "").strip()
    if not payment_reference and not payment_link_id:
        return PaymentWebhookResponse(status="ignored")

    order = find_order_for_payment_event(
        db,
        provider=provider,
        payment_reference=payment_reference,
        payment_link_id=payment_link_id,
    )
    if order is None:
        return PaymentWebhookResponse(status="ignored", payment_reference=payment_reference or None)

    integration = get_active_payment_integration(db, company_id=order.company_id)
    credentials_raw = payment_credentials_raw(integration)
    if integration and credentials_raw:
        adapter.validate_webhook_signature(
            payload,
            credentials_raw=credentials_raw,
            header_checksum=header_checksum,
        )

    transaction_id = str(transaction.get("id") or "").strip()
    if payment_event_already_processed(
        order,
        transaction_id=transaction_id or None,
        payment_reference=payment_reference or None,
    ):
        return PaymentWebhookResponse(
            status="ignored",
            order_id=str(order.id),
            payment_reference=payment_reference or order.payment_reference,
        )

    record_payment_transaction(
        order,
        transaction_id=transaction_id or None,
        payment_reference=payment_reference or order.payment_reference,
        payment_link_id=payment_link_id or None,
    )
    order = update_payment_status(
        db,
        order=order,
        payment_status=adapter.map_payment_status(transaction),
    )
    return PaymentWebhookResponse(
        status="processed",
        order_id=str(order.id),
        payment_reference=payment_reference or order.payment_reference,
    )

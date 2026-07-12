from __future__ import annotations

from sqlalchemy.orm import Session

from app.orders.service import update_payment_status
from app.payments.contract import (
    LEGACY_PAYMENT_WEBHOOK_PROVIDERS,
    LegacyPaymentWebhookAdapter,
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
    raw_body: bytes | None = None,
) -> PaymentWebhookResponse:
    normalized_provider = str(provider or "").strip().lower()
    if normalized_provider in LEGACY_PAYMENT_WEBHOOK_PROVIDERS:
        adapter = LegacyPaymentWebhookAdapter()
    else:
        adapter = get_payment_adapter(provider)
    transaction = adapter.extract_transaction(payload)
    mapped_status = adapter.map_payment_status(transaction)
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
            raw_body=raw_body,
        )

    if order.status in {"paid", "cancelled", "expired"}:
        return PaymentWebhookResponse(
            status="ignored",
            order_id=str(order.id),
            payment_reference=payment_reference or order.payment_reference,
        )

    normalized_status = mapped_status.strip().lower()
    if normalized_status in {"declined", "voided", "error", "failed"} and order.payment_status == "failed":
        return PaymentWebhookResponse(
            status="ignored",
            order_id=str(order.id),
            payment_reference=payment_reference or order.payment_reference,
        )

    transaction_id = str(transaction.get("id") or "").strip()
    if payment_event_already_processed(
        order,
        transaction_id=transaction_id or None,
        payment_reference=payment_reference or None,
        payment_link_id=payment_link_id or None,
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
        payment_status=normalized_status,
    )
    return PaymentWebhookResponse(
        status="processed",
        order_id=str(order.id),
        payment_reference=payment_reference or order.payment_reference,
    )

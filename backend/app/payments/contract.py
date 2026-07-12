from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret
from app.core.config import get_settings
from app.integrations.models import CompanyIntegration
from app.orders.models import Order
from app.payments.providers.wompi import (
    create_payment_link as create_wompi_payment_link,
    parse_credentials as parse_wompi_credentials,
    transaction_from_event,
    verify_event_checksum,
)

SUPPORTED_PAYMENT_PROVIDERS = {"wompi", "mock", "mercado_pago", "aval_pay"}
LOCAL_PAYMENT_PROVIDERS = {"mock"}
LEGACY_PAYMENT_WEBHOOK_PROVIDERS = {"stripe"}
DEFAULT_PAYMENT_LINK_TTL_MINUTES = 120


@dataclass(frozen=True)
class PaymentLinkResult:
    url: str
    reference: str
    link_id: str | None
    expires_at: datetime
    raw: dict[str, Any]


class PaymentGatewayAdapter(Protocol):
    provider: str

    def validate_integration(
        self,
        *,
        config: dict[str, Any],
        credentials_raw: str | None,
        status: str,
    ) -> None: ...

    def create_payment_link(
        self,
        *,
        credentials_raw: str | None,
        config: dict[str, Any],
        order_id: str,
        reference: str,
        amount: Decimal,
        currency: str,
    ) -> PaymentLinkResult: ...

    def extract_transaction(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def validate_webhook_signature(
        self,
        payload: dict[str, Any],
        *,
        credentials_raw: str | None,
        header_checksum: str | None,
        raw_body: bytes | None,
    ) -> None: ...

    def map_payment_status(self, transaction: dict[str, Any]) -> str: ...


def normalize_payment_provider(config: dict[str, Any] | None) -> str:
    if not isinstance(config, dict):
        return "mock"
    provider = str(config.get("provider") or "mock").strip().lower()
    return provider or "mock"


def payment_link_ttl_minutes(config: dict[str, Any] | None) -> int:
    if not isinstance(config, dict):
        return DEFAULT_PAYMENT_LINK_TTL_MINUTES
    raw_ttl = config.get("payment_link_ttl_minutes")
    if raw_ttl is None or raw_ttl == "":
        return DEFAULT_PAYMENT_LINK_TTL_MINUTES
    try:
        ttl = int(str(raw_ttl).strip())
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Payment link TTL must be a number",
        )
    if ttl < 1:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Payment link TTL must be at least 1 minute",
        )
    return ttl


def _normalize_status(status_value: str | None) -> str:
    return str(status_value or "").strip().lower() or "active"


class WompiPaymentGatewayAdapter:
    provider = "wompi"

    def validate_integration(
        self,
        *,
        config: dict[str, Any],
        credentials_raw: str | None,
        integration_status: str,
    ) -> None:
        if _normalize_status(integration_status) != "active":
            return
        credentials = parse_wompi_credentials(credentials_raw)
        if not credentials.events_secret:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Wompi events secret is required to activate this payment integration",
            )
        payment_link_ttl_minutes(config)

    def create_payment_link(
        self,
        *,
        credentials_raw: str | None,
        config: dict[str, Any],
        order_id: str,
        reference: str,
        amount: Decimal,
        currency: str,
    ) -> PaymentLinkResult:
        credentials = parse_wompi_credentials(credentials_raw)
        link = create_wompi_payment_link(
            credentials=credentials,
            environment=str(config.get("environment") or "sandbox"),
            order_id=order_id,
            reference=reference,
            amount=amount,
            currency=currency,
            redirect_url=str(config.get("redirect_url") or "").strip() or None,
            expires_in_minutes=payment_link_ttl_minutes(config),
        )
        return PaymentLinkResult(
            url=link.url,
            reference=link.reference,
            link_id=link.link_id,
            expires_at=link.expires_at,
            raw=link.raw,
        )

    def extract_transaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return transaction_from_event(payload)

    def validate_webhook_signature(
        self,
        payload: dict[str, Any],
        *,
        credentials_raw: str | None,
        header_checksum: str | None,
        raw_body: bytes | None,
    ) -> None:
        credentials = parse_wompi_credentials(credentials_raw)
        if credentials.events_secret and not verify_event_checksum(
            payload,
            events_secret=credentials.events_secret,
            header_checksum=header_checksum,
        ):
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Wompi event checksum",
            )

    def map_payment_status(self, transaction: dict[str, Any]) -> str:
        return str(transaction.get("status") or "").strip().lower()


class LocalPaymentGatewayAdapter:
    def __init__(self, provider: str) -> None:
        self.provider = provider

    def validate_integration(
        self,
        *,
        config: dict[str, Any],
        credentials_raw: str | None,
        integration_status: str,
    ) -> None:
        if _normalize_status(integration_status) != "active":
            return
        payment_link_ttl_minutes(config)
        if self.provider == "mock":
            return
        credentials = parse_wompi_credentials(credentials_raw)
        if not credentials.private_key or not credentials.events_secret:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Payment credentials are required to activate this payment integration",
            )

    def create_payment_link(
        self,
        *,
        credentials_raw: str | None,
        config: dict[str, Any],
        order_id: str,
        reference: str,
        amount: Decimal,
        currency: str,
    ) -> PaymentLinkResult:
        if self.provider in LOCAL_PAYMENT_PROVIDERS and get_settings().app_env == "production":
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Local payment provider is not allowed in production",
            )
        environment = str(config.get("environment") or "sandbox").strip().lower() or "sandbox"
        expires_at = datetime.now(UTC) + timedelta(minutes=payment_link_ttl_minutes(config))
        provider_slug = self.provider.replace("_", "-")
        if self.provider == "mock":
            checkout_host = "payments.example.test"
        else:
            checkout_host = f"{environment}.{provider_slug}.example.test"
        return PaymentLinkResult(
            url=f"https://{checkout_host}/pay/{reference}",
            reference=reference,
            link_id=None,
            expires_at=expires_at,
            raw={
                "provider": self.provider,
                "environment": environment,
                "order_id": order_id,
                "reference": reference,
                "amount": str(amount),
                "currency": currency,
                "expires_at": expires_at.isoformat(),
            },
        )

    def extract_transaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        if isinstance(payload.get("data"), dict):
            transaction = payload.get("data", {}).get("transaction")
            if isinstance(transaction, dict):
                return transaction
        return payload

    def validate_webhook_signature(
        self,
        payload: dict[str, Any],
        *,
        credentials_raw: str | None,
        header_checksum: str | None,
        raw_body: bytes | None,
    ) -> None:
        if self.provider == "mock":
            return None
        credentials = parse_wompi_credentials(credentials_raw)
        if not credentials.events_secret:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Payment webhook secret is required",
            )
        if raw_body is None:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Missing payment webhook signature",
            )
        expected_signature = "sha256=" + hmac.new(
            credentials.events_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not header_checksum or not hmac.compare_digest(header_checksum, expected_signature):
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid payment webhook signature",
            )

    def map_payment_status(self, transaction: dict[str, Any]) -> str:
        return str(transaction.get("status") or "").strip().lower() or "pending"


class LegacyPaymentWebhookAdapter:
    provider = "legacy"

    def validate_integration(
        self,
        *,
        config: dict[str, Any],
        credentials_raw: str | None,
        integration_status: str,
    ) -> None:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported payment provider",
        )

    def create_payment_link(
        self,
        *,
        credentials_raw: str | None,
        config: dict[str, Any],
        order_id: str,
        reference: str,
        amount: Decimal,
        currency: str,
    ) -> PaymentLinkResult:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported payment provider",
        )

    def extract_transaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        if isinstance(payload.get("data"), dict):
            transaction = payload.get("data", {}).get("transaction")
            if isinstance(transaction, dict):
                return transaction
        return payload

    def validate_webhook_signature(
        self,
        payload: dict[str, Any],
        *,
        credentials_raw: str | None,
        header_checksum: str | None,
        raw_body: bytes | None,
    ) -> None:
        return None

    def map_payment_status(self, transaction: dict[str, Any]) -> str:
        return str(transaction.get("status") or "").strip().lower() or "pending"


def get_payment_adapter(provider: str | None) -> PaymentGatewayAdapter:
    normalized = str(provider or "mock").strip().lower() or "mock"
    if normalized == "wompi":
        return WompiPaymentGatewayAdapter()
    if normalized in {"mock", "mercado_pago", "aval_pay"}:
        return LocalPaymentGatewayAdapter(normalized)
    raise HTTPException(
        status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Unsupported payment provider",
    )


def validate_payment_integration_config(
    *,
    config: dict[str, Any],
    credentials_raw: str | None,
    integration_status: str,
) -> None:
    if _normalize_status(integration_status) != "active":
        return
    raw_provider = str(config.get("provider") or "").strip().lower()
    if not raw_provider:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Payment provider is required",
        )
    provider = raw_provider
    if provider not in SUPPORTED_PAYMENT_PROVIDERS:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported payment provider",
        )
    if provider in LOCAL_PAYMENT_PROVIDERS and get_settings().app_env == "production":
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Local payment provider is not allowed in production",
        )
    payment_link_ttl_minutes(config)
    get_payment_adapter(provider).validate_integration(
        config=config,
        credentials_raw=credentials_raw,
        integration_status=integration_status,
    )


def get_active_payment_integration(db: Session, *, company_id: UUID) -> CompanyIntegration | None:
    return db.scalar(
        select(CompanyIntegration)
        .where(
            CompanyIntegration.company_id == company_id,
            CompanyIntegration.type == "payments",
            CompanyIntegration.status == "active",
        )
        .order_by(CompanyIntegration.updated_at.desc())
    )


def payment_credentials_raw(integration: CompanyIntegration | None) -> str | None:
    if integration is None or not integration.credentials_encrypted:
        return None
    return decrypt_secret(integration.credentials_encrypted)


def order_payment_metadata(order: Order) -> dict[str, Any]:
    metadata = order.metadata_json if isinstance(order.metadata_json, dict) else {}
    payment_metadata = metadata.get("payment", {})
    return payment_metadata if isinstance(payment_metadata, dict) else {}


def expired_payment_followup_metadata(order: Order) -> dict[str, Any]:
    payment_metadata = order_payment_metadata(order)
    follow_up = payment_metadata.get("expired_followup", {})
    return follow_up if isinstance(follow_up, dict) else {}


def expired_payment_followup_origin_order_id(order: Order) -> str | None:
    payment_metadata = order_payment_metadata(order)
    for key in ("expired_followup", "followup"):
        follow_up = payment_metadata.get(key, {})
        if not isinstance(follow_up, dict):
            continue
        origin_order_id = str(follow_up.get("origin_order_id") or "").strip()
        if origin_order_id:
            return origin_order_id
    return None


def expired_payment_followup_sent(order: Order) -> bool:
    follow_up = expired_payment_followup_metadata(order)
    return bool(follow_up.get("sent_at") or follow_up.get("claimed_at"))


def reserve_expired_payment_followup(
    order: Order,
    *,
    claimed_at: datetime,
    source: str | None = None,
) -> bool:
    metadata = dict(order.metadata_json) if isinstance(order.metadata_json, dict) else {}
    payment_metadata = dict(metadata.get("payment", {})) if isinstance(metadata.get("payment"), dict) else {}
    follow_up = dict(payment_metadata.get("expired_followup", {})) if isinstance(payment_metadata.get("expired_followup"), dict) else {}
    if follow_up.get("claimed_at") or follow_up.get("sent_at"):
        return False
    follow_up["claimed_at"] = claimed_at.isoformat()
    if source:
        follow_up["source"] = str(source).strip()
    payment_metadata["expired_followup"] = follow_up
    metadata["payment"] = payment_metadata
    order.metadata_json = metadata
    return True


def clear_expired_payment_followup_reservation(order: Order) -> None:
    metadata = dict(order.metadata_json) if isinstance(order.metadata_json, dict) else {}
    payment_metadata = dict(metadata.get("payment", {})) if isinstance(metadata.get("payment"), dict) else {}
    follow_up = dict(payment_metadata.get("expired_followup", {})) if isinstance(payment_metadata.get("expired_followup"), dict) else {}
    if "claimed_at" in follow_up and not follow_up.get("sent_at"):
        follow_up.pop("claimed_at", None)
    if not follow_up:
        payment_metadata.pop("expired_followup", None)
    else:
        payment_metadata["expired_followup"] = follow_up
    metadata["payment"] = payment_metadata
    order.metadata_json = metadata


def processed_payment_transaction_ids(order: Order) -> list[str]:
    payment_metadata = order_payment_metadata(order)
    transaction_ids = payment_metadata.get("processed_transaction_ids", [])
    if isinstance(transaction_ids, list):
        return [str(item).strip() for item in transaction_ids if str(item).strip()]
    return []


def processed_payment_references(order: Order) -> list[str]:
    payment_metadata = order_payment_metadata(order)
    references = payment_metadata.get("processed_payment_references", [])
    if isinstance(references, list):
        return [str(item).strip() for item in references if str(item).strip()]
    return []


def processed_payment_link_ids(order: Order) -> list[str]:
    payment_metadata = order_payment_metadata(order)
    link_ids = payment_metadata.get("processed_payment_link_ids", [])
    if isinstance(link_ids, list):
        return [str(item).strip() for item in link_ids if str(item).strip()]
    return []


def payment_event_already_processed(
    order: Order,
    *,
    transaction_id: str | None,
    payment_reference: str | None,
    payment_link_id: str | None,
) -> bool:
    normalized = str(transaction_id or "").strip()
    if normalized and normalized in processed_payment_transaction_ids(order):
        return True
    reference = str(payment_reference or "").strip()
    if reference and reference in processed_payment_references(order):
        return True
    normalized_link_id = str(payment_link_id or "").strip()
    if normalized_link_id and normalized_link_id in processed_payment_link_ids(order):
        return True
    return False


def record_payment_transaction(
    order: Order,
    *,
    transaction_id: str | None,
    payment_reference: str | None,
    payment_link_id: str | None = None,
) -> None:
    metadata = dict(order.metadata_json) if isinstance(order.metadata_json, dict) else {}
    payment_metadata = dict(metadata.get("payment", {})) if isinstance(metadata.get("payment"), dict) else {}
    processed_ids = processed_payment_transaction_ids(order)
    processed_references = processed_payment_references(order)
    normalized_transaction_id = str(transaction_id or "").strip()
    if normalized_transaction_id and normalized_transaction_id not in processed_ids:
        processed_ids.append(normalized_transaction_id)
        payment_metadata["processed_transaction_ids"] = processed_ids
        payment_metadata["transaction_id"] = normalized_transaction_id
    normalized_reference = str(payment_reference or "").strip()
    if normalized_reference:
        payment_metadata["transaction_reference"] = normalized_reference
    if payment_link_id:
        normalized_link_id = str(payment_link_id).strip() or None
        payment_metadata["link_id"] = normalized_link_id
        if normalized_link_id:
            processed_link_ids = processed_payment_link_ids(order)
            if normalized_link_id not in processed_link_ids:
                processed_link_ids.append(normalized_link_id)
            payment_metadata["processed_payment_link_ids"] = processed_link_ids
    if normalized_reference and not normalized_transaction_id and normalized_reference not in processed_references:
        processed_references.append(normalized_reference)
        payment_metadata["processed_payment_references"] = processed_references
    metadata["payment"] = payment_metadata
    order.metadata_json = metadata


def record_expired_payment_followup(
    order: Order,
    *,
    sent_at: datetime,
    message_id: str | None = None,
    source: str | None = None,
) -> None:
    metadata = dict(order.metadata_json) if isinstance(order.metadata_json, dict) else {}
    payment_metadata = dict(metadata.get("payment", {})) if isinstance(metadata.get("payment"), dict) else {}
    follow_up = dict(payment_metadata.get("expired_followup", {})) if isinstance(payment_metadata.get("expired_followup"), dict) else {}
    follow_up["sent_at"] = sent_at.isoformat()
    if message_id:
        follow_up["message_id"] = str(message_id).strip()
    if source:
        follow_up["source"] = str(source).strip()
    payment_metadata["expired_followup"] = follow_up
    metadata["payment"] = payment_metadata
    order.metadata_json = metadata


def order_payment_link_id(order: Order) -> str | None:
    payment_metadata = order_payment_metadata(order)
    link_id = payment_metadata.get("link_id")
    if isinstance(link_id, str) and link_id.strip():
        return link_id.strip()
    return None


def find_order_for_payment_event(
    db: Session,
    *,
    provider: str,
    payment_reference: str | None,
    payment_link_id: str | None,
) -> Order | None:
    normalized_provider = str(provider or "mock").strip().lower() or "mock"
    normalized_reference = str(payment_reference or "").strip()
    normalized_link_id = str(payment_link_id or "").strip()

    if normalized_reference:
        order = db.scalar(
            select(Order).where(
                Order.payment_reference == normalized_reference,
                Order.payment_provider == normalized_provider,
            )
        )
        if order is not None:
            return order

    if normalized_link_id:
        candidates = db.scalars(select(Order).where(Order.payment_provider == normalized_provider))
        for candidate in candidates:
            if order_payment_link_id(candidate) == normalized_link_id:
                return candidate
    return None

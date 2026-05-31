from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException, status


WOMPI_BASE_URLS = {
    "sandbox": "https://sandbox.wompi.co/v1",
    "production": "https://production.wompi.co/v1",
}


@dataclass(frozen=True)
class WompiCredentials:
    private_key: str
    events_secret: str | None = None


@dataclass(frozen=True)
class WompiPaymentLink:
    url: str
    reference: str
    link_id: str | None
    expires_at: datetime
    raw: dict[str, Any]


def parse_credentials(raw: str | None) -> WompiCredentials:
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Wompi private key is required",
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return WompiCredentials(private_key=raw.strip())

    private_key = str(parsed.get("private_key") or "").strip()
    events_secret = str(parsed.get("events_secret") or "").strip() or None
    if not private_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Wompi private key is required",
        )
    return WompiCredentials(private_key=private_key, events_secret=events_secret)


def _base_url(environment: str | None) -> str:
    return WOMPI_BASE_URLS.get((environment or "sandbox").strip().lower(), WOMPI_BASE_URLS["sandbox"])


def _amount_in_cents(total: Decimal) -> int:
    return int((total * Decimal("100")).quantize(Decimal("1")))


def create_payment_link(
    *,
    credentials: WompiCredentials,
    environment: str,
    order_id: str,
    reference: str,
    amount: Decimal,
    currency: str,
    redirect_url: str | None,
    expires_in_minutes: int = 120,
) -> WompiPaymentLink:
    expires_at = datetime.now(UTC) + timedelta(minutes=max(1, expires_in_minutes))
    payload: dict[str, Any] = {
        "name": f"Orden SwaFlow {order_id[:8]}",
        "description": f"Pago de orden {order_id}",
        "single_use": True,
        "collect_shipping": False,
        "amount_in_cents": _amount_in_cents(amount),
        "currency": currency or "COP",
        "sku": reference,
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
    }
    if redirect_url:
        payload["redirect_url"] = redirect_url

    try:
        with httpx.Client(timeout=25) as client:
            response = client.post(
                f"{_base_url(environment)}/payment_links",
                json=payload,
                headers={"Authorization": f"Bearer {credentials.private_key}"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Wompi rejected payment link: {exc.response.text[:500]}",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Wompi payment link request failed",
        ) from exc

    link_data = data.get("data", data)
    link_id = str(link_data.get("id")) if link_data.get("id") else None
    url = (
        link_data.get("permalink")
        or link_data.get("payment_url")
        or link_data.get("url")
        or link_data.get("link")
        or (f"https://checkout.wompi.co/l/{link_id}" if link_id else None)
    )
    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Wompi response did not include a payment link URL",
        )

    return WompiPaymentLink(
        url=str(url),
        reference=reference,
        link_id=link_id,
        expires_at=expires_at,
        raw=data,
    )


def nested_value(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def verify_event_checksum(payload: dict[str, Any], *, events_secret: str, header_checksum: str | None) -> bool:
    signature = payload.get("signature") if isinstance(payload.get("signature"), dict) else {}
    properties = signature.get("properties") if isinstance(signature.get("properties"), list) else []
    expected = header_checksum or signature.get("checksum")
    timestamp = payload.get("timestamp")
    if not properties or not expected or timestamp is None:
        return False
    source = "".join(str(nested_value(payload.get("data", {}), prop) or "") for prop in properties)
    source = f"{source}{timestamp}{events_secret}"
    checksum = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return checksum == str(expected)


def transaction_from_event(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    transaction = data.get("transaction") if isinstance(data.get("transaction"), dict) else data
    return transaction if isinstance(transaction, dict) else {}

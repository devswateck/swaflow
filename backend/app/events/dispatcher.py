import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.core.crypto import decrypt_secret
from app.events.models import Event
from app.integrations.models import OutboundWebhook

logger = logging.getLogger(__name__)


def _matching_outbound_webhooks(
    db: Session, *, company_id: UUID, event_type: str
) -> list[OutboundWebhook]:
    return list(
        db.scalars(
            select(OutboundWebhook).where(
                OutboundWebhook.company_id == company_id,
                OutboundWebhook.active.is_(True),
                OutboundWebhook.event_type.in_([event_type, "*"]),
            )
        )
    )


def _webhook_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def dispatch_event(db: Session, event: Event) -> None:
    webhooks = _matching_outbound_webhooks(
        db,
        company_id=event.company_id,
        event_type=event.event_type,
    )
    processed_at = datetime.now(UTC)
    if not webhooks:
        event.status = "processed"
        event.processed_at = processed_at
        db.flush()
        return

    payload = {
        "id": str(event.id),
        "event_type": event.event_type,
        "company_id": str(event.company_id),
        "payload": event.payload,
        "sent_at": processed_at.isoformat(),
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")
    delivered = 0

    with httpx.Client(timeout=5) as client:
        for webhook in webhooks:
            headers = {
                "Content-Type": "application/json",
                "X-SwaFlow-Event": event.event_type,
                "X-SwaFlow-Event-Id": str(event.id),
            }
            response: httpx.Response | None = None
            try:
                if webhook.secret_token:
                    headers["X-SwaFlow-Signature"] = _webhook_signature(
                        decrypt_secret(webhook.secret_token),
                        body,
                    )
                response = client.post(webhook.target_url, content=body, headers=headers)
                response.raise_for_status()
                delivered += 1
            except Exception:
                response_status_code = response.status_code if response is not None else None
                try:
                    record_audit(
                        db,
                        company_id=event.company_id,
                        actor_user=None,
                        action="outbound_webhook.delivery_failed",
                        entity_type="outbound_webhook",
                        entity_id=webhook.id,
                        summary="Outbound webhook delivery failed",
                        metadata={
                            "event_id": str(event.id),
                            "event_type": event.event_type,
                            "target_url": webhook.target_url,
                            "failure_type": "delivery_failed",
                            "response_status_code": response_status_code,
                        },
                    )
                except Exception:
                    logger.exception(
                        "Failed to persist outbound webhook delivery incident for event_id=%s webhook_id=%s",
                        event.id,
                        webhook.id,
                    )
                continue

    event.status = "processed" if delivered == len(webhooks) else "delivery_failed"
    event.processed_at = datetime.now(UTC)
    db.flush()

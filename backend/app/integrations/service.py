import json
import re
from collections.abc import Mapping
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret, encrypt_secret
from app.audit.service import record_audit_best_effort
from app.integrations.calendar import normalize_calendar_config, validate_calendar_integration_config
from app.integrations.models import CompanyIntegration, OutboundWebhook
from app.integrations.schemas import (
    IntegrationCreate,
    IntegrationUpdate,
    OutboundWebhookCreate,
    OutboundWebhookUpdate,
)
from app.payments.contract import validate_payment_integration_config

_SENSITIVE_KEY_NAMES = (
    "credential",
    "credentials",
    "password",
    "private_key",
    "secret",
    "secret_token",
    "token",
    "access_token",
    "signature",
    "api_key",
    "client_secret",
)
_SAFE_AUDIT_FLAGS = {
    "credentials_configured",
    "secret_configured",
    "app_secret_configured",
    "signature_algorithm",
    "token_count",
}


def _normalize_key_name(key: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key).lower()


def list_integrations(db: Session, *, company_id: UUID) -> list[CompanyIntegration]:
    return list(
        db.scalars(
            select(CompanyIntegration)
            .where(CompanyIntegration.company_id == company_id)
            .order_by(CompanyIntegration.created_at.desc())
        )
    )


def create_integration(
    db: Session,
    *,
    company_id: UUID,
    payload: IntegrationCreate,
    actor_user=None,
) -> CompanyIntegration:
    raw_config = payload.config if isinstance(payload.config, dict) else {}
    config = normalize_calendar_config(raw_config) if payload.type == "calendar" else payload.config
    credentials_raw = payload.credentials
    if payload.type == "payments":
        validate_payment_integration_config(
            config=config,
            credentials_raw=credentials_raw,
            integration_status="active",
        )
    if payload.type == "calendar":
        validate_calendar_integration_config(
            config=raw_config,
            credentials_raw=credentials_raw,
            integration_status="active",
        )
    if payload.type == "payments":
        config = payload.config
    integration = CompanyIntegration(
        company_id=company_id,
        type=payload.type,
        credentials_encrypted=encrypt_secret(credentials_raw) if credentials_raw else None,
        config=config,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="integration.created",
        entity_type="integration",
        summary="Integration created",
        entity_id=integration.id,
        metadata=_safe_audit_metadata(payload.model_dump()),
    )
    return integration


def _merge_secret_payload(current: str | None, incoming: str) -> str:
    try:
        incoming_data = json.loads(incoming)
    except json.JSONDecodeError:
        return incoming
    if not isinstance(incoming_data, dict):
        return incoming

    current_data: dict = {}
    if current:
        try:
            decoded = decrypt_secret(current)
            parsed = json.loads(decoded)
            if isinstance(parsed, dict):
                current_data = parsed
        except Exception:
            current_data = {}

    for key, value in incoming_data.items():
        if value not in {None, ""}:
            current_data[key] = value
    return json.dumps(current_data)


def _safe_audit_metadata(data: dict) -> dict:
    def _is_sensitive_key(key: object) -> bool:
        if not isinstance(key, str):
            return False
        normalized = _normalize_key_name(key)
        if normalized in _SAFE_AUDIT_FLAGS:
            return False
        return any(
            re.search(rf"(^|[._-]){re.escape(fragment)}([._-]|$)", normalized) is not None
            for fragment in _SENSITIVE_KEY_NAMES
        )

    def _sanitize(value):
        if isinstance(value, Mapping):
            return {
                key: _sanitize(child)
                for key, child in value.items()
                if not _is_sensitive_key(key)
            }
        if isinstance(value, list):
            return [_sanitize(item) for item in value]
        if isinstance(value, tuple):
            return tuple(_sanitize(item) for item in value)
        return value

    return jsonable_encoder(_sanitize(dict(data)))


def get_integration(db: Session, *, company_id: UUID, integration_id: UUID) -> CompanyIntegration:
    integration = db.scalar(
        select(CompanyIntegration).where(
            CompanyIntegration.company_id == company_id,
            CompanyIntegration.id == integration_id,
        )
    )
    if integration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    return integration


def update_integration(
    db: Session,
    *,
    company_id: UUID,
    integration_id: UUID,
    payload: IntegrationUpdate,
    actor_user=None,
) -> CompanyIntegration:
    integration = get_integration(db, company_id=company_id, integration_id=integration_id)
    data = payload.model_dump(exclude_unset=True)
    raw_next_config = data.get("config") if data.get("config") is not None else integration.config
    next_config = raw_next_config
    if isinstance(next_config, dict) is False:
        next_config = integration.config if isinstance(integration.config, dict) else {}
    if integration.type == "calendar":
        next_config = normalize_calendar_config(next_config)
    next_status = str(data.get("status") or integration.status or "active")
    next_credentials_raw: str | None
    if "credentials" in data:
        credentials = data.get("credentials")
        if credentials:
            next_credentials_raw = _merge_secret_payload(integration.credentials_encrypted, credentials)
        else:
            next_credentials_raw = None
    else:
        next_credentials_raw = decrypt_secret(integration.credentials_encrypted) if integration.credentials_encrypted else None
    if integration.type == "payments":
        validate_payment_integration_config(
            config=next_config,
            credentials_raw=next_credentials_raw,
            integration_status=next_status,
        )
    if integration.type == "calendar":
        validate_calendar_integration_config(
            config=raw_next_config if isinstance(raw_next_config, dict) else {},
            credentials_raw=next_credentials_raw,
            integration_status=next_status,
        )
    if "credentials" in data:
        credentials = data.pop("credentials")
        if credentials:
            integration.credentials_encrypted = encrypt_secret(
                _merge_secret_payload(integration.credentials_encrypted, credentials)
            )
        elif credentials is None:
            integration.credentials_encrypted = None
    for field, value in data.items():
        if field == "config" and integration.type == "calendar" and isinstance(value, dict):
            value = normalize_calendar_config(value)
        setattr(integration, field, value)
    db.commit()
    db.refresh(integration)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="integration.updated",
        entity_type="integration",
        entity_id=integration.id,
        summary="Integration updated",
        metadata=_safe_audit_metadata(payload.model_dump(exclude_unset=True)),
    )
    return integration


def list_outbound_webhooks(db: Session, *, company_id: UUID) -> list[OutboundWebhook]:
    return list(
        db.scalars(
            select(OutboundWebhook)
            .where(OutboundWebhook.company_id == company_id)
            .order_by(OutboundWebhook.created_at.desc())
        )
    )


def create_outbound_webhook(
    db: Session,
    *,
    company_id: UUID,
    payload: OutboundWebhookCreate,
    actor_user=None,
) -> OutboundWebhook:
    webhook = OutboundWebhook(
        company_id=company_id,
        event_type=payload.event_type,
        target_url=str(payload.target_url),
        secret_token=encrypt_secret(payload.secret_token) if payload.secret_token else None,
        active=payload.active,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="outbound_webhook.created",
        entity_type="outbound_webhook",
        entity_id=webhook.id,
        summary="Outbound webhook created",
        metadata=_safe_audit_metadata(payload.model_dump()),
    )
    return webhook


def get_outbound_webhook(db: Session, *, company_id: UUID, webhook_id: UUID) -> OutboundWebhook:
    webhook = db.scalar(
        select(OutboundWebhook).where(
            OutboundWebhook.company_id == company_id,
            OutboundWebhook.id == webhook_id,
        )
    )
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return webhook


def update_outbound_webhook(
    db: Session,
    *,
    company_id: UUID,
    webhook_id: UUID,
    payload: OutboundWebhookUpdate,
    actor_user=None,
) -> OutboundWebhook:
    webhook = get_outbound_webhook(db, company_id=company_id, webhook_id=webhook_id)
    data = payload.model_dump(exclude_unset=True)
    if "secret_token" in data:
        secret_token = data.pop("secret_token")
        webhook.secret_token = encrypt_secret(secret_token) if secret_token else None
    if "target_url" in data and data["target_url"] is not None:
        data["target_url"] = str(data["target_url"])
    for field, value in data.items():
        setattr(webhook, field, value)
    db.commit()
    db.refresh(webhook)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="outbound_webhook.updated",
        entity_type="outbound_webhook",
        entity_id=webhook.id,
        summary="Outbound webhook updated",
        metadata=_safe_audit_metadata(payload.model_dump(exclude_unset=True)),
    )
    return webhook


def delete_outbound_webhook(
    db: Session,
    *,
    company_id: UUID,
    webhook_id: UUID,
    actor_user=None,
) -> None:
    webhook = get_outbound_webhook(db, company_id=company_id, webhook_id=webhook_id)
    db.delete(webhook)
    db.commit()
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="outbound_webhook.deleted",
        entity_type="outbound_webhook",
        entity_id=webhook.id,
        summary="Outbound webhook deleted",
        metadata={"event_type": webhook.event_type, "target_url": webhook.target_url},
    )

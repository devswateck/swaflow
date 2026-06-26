import json
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret, encrypt_secret
from app.audit.service import record_audit
from app.integrations.models import CompanyIntegration, OutboundWebhook
from app.integrations.schemas import (
    IntegrationCreate,
    IntegrationUpdate,
    OutboundWebhookCreate,
    OutboundWebhookUpdate,
)
from app.payments.contract import validate_payment_integration_config


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
    if payload.type == "payments":
        validate_payment_integration_config(
            config=payload.config,
            credentials_raw=payload.credentials,
            integration_status="active",
        )
    integration = CompanyIntegration(
        company_id=company_id,
        type=payload.type,
        credentials_encrypted=encrypt_secret(payload.credentials) if payload.credentials else None,
        config=payload.config,
    )
    db.add(integration)
    record_audit(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="integration.created",
        entity_type="integration",
        summary="Integration created",
        entity_id=integration.id,
        metadata={"type": payload.type, "status": "active"},
    )
    db.commit()
    db.refresh(integration)
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
    safe_data = dict(data)
    safe_data.pop("credentials", None)
    safe_data.pop("secret_token", None)
    return safe_data


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
    next_config = data.get("config") if data.get("config") is not None else integration.config
    if isinstance(next_config, dict) is False:
        next_config = integration.config if isinstance(integration.config, dict) else {}
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
    if "credentials" in data:
        credentials = data.pop("credentials")
        if credentials:
            integration.credentials_encrypted = encrypt_secret(
                _merge_secret_payload(integration.credentials_encrypted, credentials)
            )
        elif credentials is None:
            integration.credentials_encrypted = None
    for field, value in data.items():
        setattr(integration, field, value)
    record_audit(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="integration.updated",
        entity_type="integration",
        entity_id=integration.id,
        summary="Integration updated",
        metadata=_safe_audit_metadata(payload.model_dump(exclude_unset=True)),
    )
    db.commit()
    db.refresh(integration)
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
    record_audit(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="outbound_webhook.created",
        entity_type="outbound_webhook",
        entity_id=webhook.id,
        summary="Outbound webhook created",
        metadata={"event_type": payload.event_type, "target_url": str(payload.target_url)},
    )
    db.commit()
    db.refresh(webhook)
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
    record_audit(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="outbound_webhook.updated",
        entity_type="outbound_webhook",
        entity_id=webhook.id,
        summary="Outbound webhook updated",
        metadata=_safe_audit_metadata(payload.model_dump(exclude_unset=True)),
    )
    db.commit()
    db.refresh(webhook)
    return webhook


def delete_outbound_webhook(
    db: Session,
    *,
    company_id: UUID,
    webhook_id: UUID,
    actor_user=None,
) -> None:
    webhook = get_outbound_webhook(db, company_id=company_id, webhook_id=webhook_id)
    record_audit(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="outbound_webhook.deleted",
        entity_type="outbound_webhook",
        entity_id=webhook.id,
        summary="Outbound webhook deleted",
        metadata={"event_type": webhook.event_type, "target_url": webhook.target_url},
    )
    db.delete(webhook)
    db.commit()

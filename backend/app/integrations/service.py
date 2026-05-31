import json
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret, encrypt_secret
from app.integrations.models import CompanyIntegration, OutboundWebhook
from app.integrations.schemas import (
    IntegrationCreate,
    IntegrationUpdate,
    OutboundWebhookCreate,
    OutboundWebhookUpdate,
)


def list_integrations(db: Session, *, company_id: UUID) -> list[CompanyIntegration]:
    return list(
        db.scalars(
            select(CompanyIntegration)
            .where(CompanyIntegration.company_id == company_id)
            .order_by(CompanyIntegration.created_at.desc())
        )
    )


def create_integration(
    db: Session, *, company_id: UUID, payload: IntegrationCreate
) -> CompanyIntegration:
    integration = CompanyIntegration(
        company_id=company_id,
        type=payload.type,
        credentials_encrypted=encrypt_secret(payload.credentials) if payload.credentials else None,
        config=payload.config,
    )
    db.add(integration)
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
    db: Session, *, company_id: UUID, integration_id: UUID, payload: IntegrationUpdate
) -> CompanyIntegration:
    integration = get_integration(db, company_id=company_id, integration_id=integration_id)
    data = payload.model_dump(exclude_unset=True)
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
    db: Session, *, company_id: UUID, payload: OutboundWebhookCreate
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
    db: Session, *, company_id: UUID, webhook_id: UUID, payload: OutboundWebhookUpdate
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
    return webhook


def delete_outbound_webhook(db: Session, *, company_id: UUID, webhook_id: UUID) -> None:
    webhook = get_outbound_webhook(db, company_id=company_id, webhook_id=webhook_id)
    db.delete(webhook)
    db.commit()

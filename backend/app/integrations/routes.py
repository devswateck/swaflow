from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.core.database import get_db
from app.core.schemas import MessageResponse
from app.integrations import service
from app.integrations.models import CompanyIntegration, OutboundWebhook
from app.integrations.schemas import (
    IntegrationCreate,
    IntegrationRead,
    IntegrationUpdate,
    OutboundWebhookCreate,
    OutboundWebhookRead,
    OutboundWebhookUpdate,
)
from app.users.models import User

router = APIRouter(tags=["integrations"])


@router.get("/integrations", response_model=list[IntegrationRead])
def list_integrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CompanyIntegration]:
    return service.list_integrations(db, company_id=current_user.company_id)


@router.post("/integrations", response_model=IntegrationRead, status_code=201)
def create_integration(
    payload: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyIntegration:
    return service.create_integration(db, company_id=current_user.company_id, payload=payload)


@router.put("/integrations/{integration_id}", response_model=IntegrationRead)
def update_integration(
    integration_id: UUID,
    payload: IntegrationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyIntegration:
    return service.update_integration(
        db, company_id=current_user.company_id, integration_id=integration_id, payload=payload
    )


@router.get("/outbound-webhooks", response_model=list[OutboundWebhookRead])
def list_outbound_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OutboundWebhook]:
    return service.list_outbound_webhooks(db, company_id=current_user.company_id)


@router.post("/outbound-webhooks", response_model=OutboundWebhookRead, status_code=201)
def create_outbound_webhook(
    payload: OutboundWebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutboundWebhook:
    return service.create_outbound_webhook(db, company_id=current_user.company_id, payload=payload)


@router.put("/outbound-webhooks/{webhook_id}", response_model=OutboundWebhookRead)
def update_outbound_webhook(
    webhook_id: UUID,
    payload: OutboundWebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutboundWebhook:
    return service.update_outbound_webhook(
        db, company_id=current_user.company_id, webhook_id=webhook_id, payload=payload
    )


@router.delete("/outbound-webhooks/{webhook_id}", response_model=MessageResponse)
def delete_outbound_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service.delete_outbound_webhook(db, company_id=current_user.company_id, webhook_id=webhook_id)
    return MessageResponse(detail="Webhook deleted")


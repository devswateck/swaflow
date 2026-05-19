from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.users.models import User
from app.whatsapp import service
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.schemas import (
    WhatsAppAccountCreate,
    WhatsAppAccountRead,
    WhatsAppWebhookResponse,
)

router = APIRouter(tags=["whatsapp"])


@router.get("/webhooks/whatsapp")
def verify_whatsapp_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    settings = get_settings()
    valid_global_token = bool(settings.whatsapp_verify_token) and (
        verify_token == settings.whatsapp_verify_token
    )
    valid_account_token = bool(verify_token) and service.verify_token_exists(
        db, verify_token=verify_token
    )
    if mode == "subscribe" and challenge and (valid_global_token or valid_account_token):
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid verify token")


@router.post("/webhooks/whatsapp", response_model=WhatsAppWebhookResponse)
async def receive_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> WhatsAppWebhookResponse:
    payload = await request.json()
    processed, skipped = service.process_webhook_payload(db, payload=payload)
    return WhatsAppWebhookResponse(processed=processed, skipped=skipped)


@router.post("/whatsapp/accounts", response_model=WhatsAppAccountRead, status_code=201)
def create_whatsapp_account(
    payload: WhatsAppAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WhatsAppAccount:
    return service.create_account(db, company_id=current_user.company_id, payload=payload)


@router.get("/whatsapp/accounts", response_model=list[WhatsAppAccountRead])
def list_whatsapp_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WhatsAppAccount]:
    return service.list_accounts(db, company_id=current_user.company_id)


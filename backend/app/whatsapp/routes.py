import hashlib
import hmac
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.auth.service import require_module_access
from app.core.config import get_settings
from app.core.database import get_db
from app.users.models import User
from app.whatsapp import service
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.schemas import (
    WhatsAppAccountCreate,
    WhatsAppAccountTestRead,
    WhatsAppAccountRead,
    WhatsAppCatalogSyncRequest,
    WhatsAppCatalogSyncResponse,
    WhatsAppSendButtonsRequest,
    WhatsAppSendProductCardsFromDbRequest,
    WhatsAppSendProductCardsRequest,
    WhatsAppSendTextRequest,
    WhatsAppSendTextResponse,
    WhatsAppSetupRead,
    WhatsAppWebhookResponse,
)

router = APIRouter(tags=["whatsapp"])


def verify_webhook_signature(*, body: bytes, signature: str | None) -> None:
    settings = get_settings()
    if not settings.whatsapp_app_secret:
        return
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")
    digest = hmac.new(
        settings.whatsapp_app_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, f"sha256={digest}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


@router.get("/webhooks/whatsapp")
def verify_whatsapp_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    settings = get_settings()
    if mode == "subscribe" and challenge:
        if settings.whatsapp_verify_token:
            if verify_token == settings.whatsapp_verify_token:
                return PlainTextResponse(challenge)
        elif verify_token and service.verify_token_exists(db, verify_token=verify_token):
            return PlainTextResponse(challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid verify token")


@router.post("/webhooks/whatsapp", response_model=WhatsAppWebhookResponse)
async def receive_whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> WhatsAppWebhookResponse:
    body = await request.body()
    verify_webhook_signature(body=body, signature=x_hub_signature_256)
    payload = json.loads(body or "{}")
    processed, skipped = service.process_webhook_payload(db, payload=payload)
    return WhatsAppWebhookResponse(processed=processed, skipped=skipped)


@router.get("/whatsapp/setup", response_model=WhatsAppSetupRead)
def get_whatsapp_setup(
    current_user: User = Depends(require_module_access("whatsapp")),
) -> WhatsAppSetupRead:
    settings = get_settings()
    return WhatsAppSetupRead(
        callback_url=f"{settings.public_base_url.rstrip('/')}/webhooks/whatsapp",
        verify_token=settings.whatsapp_verify_token,
        graph_api_version=settings.whatsapp_graph_api_version,
        app_secret_configured=bool(settings.whatsapp_app_secret),
    )


@router.post("/whatsapp/accounts", response_model=WhatsAppAccountRead, status_code=201)
def create_whatsapp_account(
    payload: WhatsAppAccountCreate,
    current_user: User = Depends(require_module_access("whatsapp")),
    db: Session = Depends(get_db),
) -> WhatsAppAccount:
    return service.create_account(db, company_id=current_user.company_id, payload=payload)


@router.get("/whatsapp/accounts", response_model=list[WhatsAppAccountRead])
def list_whatsapp_accounts(
    current_user: User = Depends(require_module_access("whatsapp")),
    db: Session = Depends(get_db),
) -> list[WhatsAppAccount]:
    return service.list_accounts(db, company_id=current_user.company_id)


@router.post("/whatsapp/accounts/{account_id}/test", response_model=WhatsAppAccountTestRead)
def test_whatsapp_account(
    account_id: UUID,
    current_user: User = Depends(require_module_access("whatsapp")),
    db: Session = Depends(get_db),
) -> WhatsAppAccountTestRead:
    return service.test_account(db, company_id=current_user.company_id, account_id=account_id)


@router.post("/whatsapp/messages", response_model=WhatsAppSendTextResponse)
def send_whatsapp_message(
    payload: WhatsAppSendTextRequest,
    current_user: User = Depends(require_module_access("whatsapp")),
    db: Session = Depends(get_db),
) -> WhatsAppSendTextResponse:
    return service.send_text_message(db, company_id=current_user.company_id, payload=payload)


@router.post("/whatsapp/messages/buttons", response_model=WhatsAppSendTextResponse)
def send_whatsapp_buttons(
    payload: WhatsAppSendButtonsRequest,
    current_user: User = Depends(require_module_access("whatsapp")),
    db: Session = Depends(get_db),
) -> WhatsAppSendTextResponse:
    return service.send_buttons_message(db, company_id=current_user.company_id, payload=payload)


@router.post("/whatsapp/messages/product-cards", response_model=WhatsAppSendTextResponse)
def send_whatsapp_product_cards(
    payload: WhatsAppSendProductCardsRequest,
    current_user: User = Depends(require_module_access("whatsapp")),
    db: Session = Depends(get_db),
) -> WhatsAppSendTextResponse:
    return service.send_product_cards_message(
        db, company_id=current_user.company_id, payload=payload
    )


@router.post("/whatsapp/messages/product-cards/db", response_model=WhatsAppSendTextResponse)
def send_whatsapp_product_cards_from_db(
    payload: WhatsAppSendProductCardsFromDbRequest,
    current_user: User = Depends(require_module_access("whatsapp")),
    db: Session = Depends(get_db),
) -> WhatsAppSendTextResponse:
    return service.send_product_cards_from_db(
        db, company_id=current_user.company_id, payload=payload
    )


@router.post("/whatsapp/catalog/sync", response_model=WhatsAppCatalogSyncResponse)
def sync_whatsapp_catalog(
    payload: WhatsAppCatalogSyncRequest,
    current_user: User = Depends(require_module_access("whatsapp")),
    db: Session = Depends(get_db),
) -> WhatsAppCatalogSyncResponse:
    return service.sync_catalog_products(
        db, company_id=current_user.company_id, payload=payload
    )

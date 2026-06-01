from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import TimestampedRead


class WhatsAppAccountCreate(BaseModel):
    phone_number_id: str = Field(min_length=1, max_length=100)
    business_account_id: str | None = Field(default=None, max_length=100)
    access_token: str = Field(min_length=1)
    verify_token: str | None = Field(default=None, min_length=8, max_length=255)

    @field_validator("verify_token", mode="before")
    @classmethod
    def reject_meta_access_token_as_verify_token(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value

        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned.startswith("EAA"):
            raise ValueError(
                "El verify token no es el access token de Meta. "
                "Pega el token EAA en Access token."
            )
        return cleaned


class WhatsAppAccountRead(TimestampedRead):
    company_id: UUID
    phone_number_id: str
    business_account_id: str | None
    verify_token: str
    status: str


class WhatsAppWebhookResponse(BaseModel):
    processed: int
    skipped: int


class WhatsAppSetupRead(BaseModel):
    callback_url: str
    verify_token: str | None
    graph_api_version: str
    app_secret_configured: bool


class WhatsAppAccountTestRead(BaseModel):
    ok: bool
    phone_number_id: str
    display_phone_number: str | None = None
    verified_name: str | None = None
    quality_rating: str | None = None
    raw: dict = Field(default_factory=dict)


class WhatsAppSendTextRequest(BaseModel):
    to: str = Field(min_length=8, max_length=30)
    body: str = Field(min_length=1, max_length=4096)
    account_id: UUID | None = None


class WhatsAppSendTextResponse(BaseModel):
    ok: bool
    meta_message_id: str | None = None
    contact_id: UUID
    conversation_id: UUID
    message_id: UUID
    raw: dict = Field(default_factory=dict)


class WhatsAppButtonOption(BaseModel):
    id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=20)


class WhatsAppSendButtonsRequest(BaseModel):
    to: str = Field(min_length=8, max_length=30)
    body: str = Field(min_length=1, max_length=1024)
    footer: str | None = Field(default=None, max_length=60)
    buttons: list[WhatsAppButtonOption] = Field(min_length=1, max_length=3)
    account_id: UUID | None = None


class WhatsAppProductCardItem(BaseModel):
    product_retailer_id: str = Field(min_length=1, max_length=200)


class WhatsAppSendProductCardsRequest(BaseModel):
    to: str = Field(min_length=8, max_length=30)
    body: str = Field(min_length=1, max_length=1024)
    catalog_id: str = Field(min_length=1, max_length=100)
    button_text: str = Field(default="Ver productos", min_length=1, max_length=20)
    section_title: str = Field(default="Catalogo", min_length=1, max_length=24)
    items: list[WhatsAppProductCardItem] = Field(min_length=1, max_length=10)
    account_id: UUID | None = None


class WhatsAppSendProductCardsFromDbRequest(BaseModel):
    to: str = Field(min_length=8, max_length=30)
    body: str = Field(min_length=1, max_length=1024)
    button_text: str = Field(default="Ver productos", min_length=1, max_length=20)
    section_title: str = Field(default="Catalogo", min_length=1, max_length=24)
    product_ids: list[UUID] = Field(min_length=1, max_length=10)
    account_id: UUID | None = None


class WhatsAppCatalogSyncRequest(BaseModel):
    catalog_id: str = Field(min_length=1, max_length=100)
    account_id: UUID | None = None


class WhatsAppCatalogSyncResponse(BaseModel):
    fetched: int
    created: int
    updated: int
    warning: str | None = None

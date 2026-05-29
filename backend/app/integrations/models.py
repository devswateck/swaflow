from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class CompanyIntegration(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "company_integrations"

    type: Mapped[str] = mapped_column(String(100), nullable=False)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    @property
    def credentials_configured(self) -> bool:
        return bool(self.credentials_encrypted)


class OutboundWebhook(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "outbound_webhooks"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    secret_token: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def secret_configured(self) -> bool:
        return bool(self.secret_token)

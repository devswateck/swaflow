from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class WhatsAppAccount(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "whatsapp_accounts"

    phone_number_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    business_account_id: Mapped[str | None] = mapped_column(String(100))
    access_token_encrypted: Mapped[str] = mapped_column(nullable=False)
    verify_token: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")


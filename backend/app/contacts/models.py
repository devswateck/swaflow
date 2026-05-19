from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class Contact(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("company_id", "phone", name="uq_contacts_company_phone"),)

    name: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="whatsapp")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


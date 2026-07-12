from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models import IdMixin, TimestampMixin


class Company(Base, IdMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    business_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    auto_assign_single_additional_user_chats: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="company")

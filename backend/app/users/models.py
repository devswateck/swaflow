from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class User(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("company_id", "email", name="uq_users_company_email"),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="agent")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    company: Mapped["Company"] = relationship(back_populates="users")


from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class AiAgent(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ai_agents"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str | None] = mapped_column(String(100))
    rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


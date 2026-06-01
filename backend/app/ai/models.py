from sqlalchemy import JSON, Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import IdMixin, TenantMixin, TimestampMixin


class AiAgent(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ai_agents"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    conversation_guide: Mapped[str] = mapped_column(Text, nullable=False, default="")
    security_rules: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tone: Mapped[str | None] = mapped_column(String(100))
    rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AiInteractiveTemplate(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ai_interactive_templates"
    __table_args__ = (
        UniqueConstraint("company_id", "action_key", name="uq_ai_interactive_templates_company_action"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    action_key: Mapped[str] = mapped_column(String(120), nullable=False)
    template_type: Mapped[str] = mapped_column(String(20), nullable=False, default="buttons")
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    footer_text: Mapped[str | None] = mapped_column(String(60))
    button_text: Mapped[str | None] = mapped_column(String(20))
    section_title: Mapped[str | None] = mapped_column(String(24))
    options: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    usage_instruction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    trigger_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="ai_decides")
    trigger_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AiFaqEntry(Base, IdMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ai_faq_entries"

    question: Mapped[str] = mapped_column(String(300), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

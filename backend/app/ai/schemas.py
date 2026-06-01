from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import TimestampedRead


class AiAgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    system_prompt: str = Field(min_length=1)
    conversation_objective: str = Field(default="", max_length=6000)
    conversation_guide: str = Field(default="", max_length=12000)
    security_rules: str = Field(default="", max_length=6000)
    tone: str | None = Field(default=None, max_length=100)
    rules: dict = Field(default_factory=dict)
    active: bool = True


class AiAgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    system_prompt: str | None = Field(default=None, min_length=1)
    conversation_objective: str | None = Field(default=None, max_length=6000)
    conversation_guide: str | None = Field(default=None, max_length=12000)
    security_rules: str | None = Field(default=None, max_length=6000)
    tone: str | None = Field(default=None, max_length=100)
    rules: dict | None = None
    active: bool | None = None


class AiAgentRead(TimestampedRead):
    company_id: UUID
    name: str
    system_prompt: str
    conversation_objective: str
    conversation_guide: str
    security_rules: str
    tone: str | None
    rules: dict
    active: bool


class AiFaqEntryCreate(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    answer: str = Field(min_length=1, max_length=8000)
    active: bool = True


class AiFaqEntryUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=300)
    answer: str | None = Field(default=None, min_length=1, max_length=8000)
    active: bool | None = None


class AiFaqEntryRead(TimestampedRead):
    company_id: UUID
    question: str
    answer: str
    active: bool


class AiFaqUploadResult(BaseModel):
    total_read: int
    created: int
    updated: int


class AiInteractiveTemplateOption(BaseModel):
    id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=24)
    description: str | None = Field(default=None, max_length=72)


class AiInteractiveTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    action_key: str = Field(min_length=1, max_length=120)
    template_type: str = Field(default="buttons", pattern="^(buttons|list)$")
    body_text: str = Field(min_length=1, max_length=1024)
    footer_text: str | None = Field(default=None, max_length=60)
    button_text: str | None = Field(default="Ver opciones", max_length=20)
    section_title: str | None = Field(default="Opciones", max_length=24)
    options: list[AiInteractiveTemplateOption] = Field(min_length=1, max_length=10)
    usage_instruction: str = Field(default="", max_length=500)
    trigger_mode: str = Field(default="ai_decides", pattern="^(ai_decides|after_capture)$")
    trigger_fields: list[str] = Field(default_factory=list, max_length=12)
    active: bool = True


class AiInteractiveTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    action_key: str | None = Field(default=None, min_length=1, max_length=120)
    template_type: str | None = Field(default=None, pattern="^(buttons|list)$")
    body_text: str | None = Field(default=None, min_length=1, max_length=1024)
    footer_text: str | None = Field(default=None, max_length=60)
    button_text: str | None = Field(default=None, max_length=20)
    section_title: str | None = Field(default=None, max_length=24)
    options: list[AiInteractiveTemplateOption] | None = Field(default=None, min_length=1, max_length=10)
    usage_instruction: str | None = Field(default=None, max_length=500)
    trigger_mode: str | None = Field(default=None, pattern="^(ai_decides|after_capture)$")
    trigger_fields: list[str] | None = Field(default=None, max_length=12)
    active: bool | None = None


class AiInteractiveTemplateRead(TimestampedRead):
    company_id: UUID
    name: str
    action_key: str
    template_type: str
    body_text: str
    footer_text: str | None
    button_text: str | None
    section_title: str | None
    options: list[AiInteractiveTemplateOption]
    usage_instruction: str
    trigger_mode: str
    trigger_fields: list[str]
    active: bool


class IntentClassifyRequest(BaseModel):
    message: str = Field(min_length=1)


class IntentClassifyResponse(BaseModel):
    intent: str
    confidence: float
    entities: dict


class ProductToolRead(BaseModel):
    id: UUID
    name: str
    price: Decimal
    currency: str
    available: bool


class SearchProductsToolResponse(BaseModel):
    products: list[ProductToolRead]


class CheckStockToolResponse(BaseModel):
    available: bool
    quantity_available: int


class ScheduleAppointmentToolRequest(BaseModel):
    contact_id: UUID
    conversation_id: UUID | None = None
    scheduled_at: datetime
    notes: str | None = None

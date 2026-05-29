from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import TimestampedRead


class FunnelStepWrite(BaseModel):
    position: int = Field(default=1, ge=1, le=200)
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=120)
    prompt: str = ""
    objectives: list[str] = Field(default_factory=list)
    transition_criteria: str = ""
    status: str = Field(default="active", max_length=30)
    config: dict = Field(default_factory=dict)


class FunnelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    status: str = Field(default="active", max_length=30)
    is_default: bool = False
    steps: list[FunnelStepWrite] = Field(default_factory=list)


class FunnelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    status: str | None = Field(default=None, max_length=30)
    is_default: bool | None = None
    steps: list[FunnelStepWrite] | None = None


class FunnelStepRead(TimestampedRead):
    company_id: UUID
    funnel_id: UUID
    position: int
    name: str
    code: str
    prompt: str
    objectives: list[str]
    transition_criteria: str
    status: str
    config: dict


class FunnelRead(TimestampedRead):
    company_id: UUID
    name: str
    description: str | None
    status: str
    is_default: bool
    steps: list[FunnelStepRead]

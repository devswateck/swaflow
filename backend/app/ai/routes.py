from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.ai import service
from app.ai.models import AiAgent, AiFaqEntry
from app.ai.schemas import (
    AiAgentCreate,
    AiAgentRead,
    AiAgentUpdate,
    AiFaqEntryCreate,
    AiFaqEntryRead,
    AiFaqEntryUpdate,
    AiFaqUploadResult,
    AiInteractiveTemplateCreate,
    AiInteractiveTemplateRead,
    AiInteractiveTemplateUpdate,
    AiOperationalConfigRead,
    AiOperationalSimulationRequest,
    AiOperationalSimulationResponse,
    DefaultSystemPromptRead,
    CheckStockToolResponse,
    IntentClassifyRequest,
    IntentClassifyResponse,
    SearchProductsToolResponse,
)
from app.ai.prompts import DEFAULT_SYSTEM_PROMPT
from app.ai.tools import check_stock_tool, search_products_tool
from app.auth.service import require_module_access
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/prompts/default-system-prompt", response_model=DefaultSystemPromptRead)
def get_default_system_prompt(
    current_user: User = Depends(require_module_access("ai")),
) -> DefaultSystemPromptRead:
    return DefaultSystemPromptRead(default_system_prompt=DEFAULT_SYSTEM_PROMPT)


@router.get("/agents", response_model=list[AiAgentRead])
def list_agents(
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> list[AiAgent]:
    return service.list_agents(db, company_id=current_user.company_id)


@router.post("/agents", response_model=AiAgentRead, status_code=201)
def create_agent(
    payload: AiAgentCreate,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> AiAgent:
    return service.create_agent(db, company_id=current_user.company_id, payload=payload)


@router.put("/agents/{agent_id}", response_model=AiAgentRead)
def update_agent(
    agent_id: UUID,
    payload: AiAgentUpdate,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> AiAgent:
    return service.update_agent(
        db, company_id=current_user.company_id, agent_id=agent_id, payload=payload
    )


@router.get("/agents/{agent_id}/operational-config", response_model=AiOperationalConfigRead)
def get_operational_config(
    agent_id: UUID,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> AiOperationalConfigRead:
    return service.get_operational_config(
        db,
        company_id=current_user.company_id,
        agent_id=agent_id,
    )


@router.put("/agents/{agent_id}/operational-config", response_model=AiAgentRead)
def update_operational_config(
    agent_id: UUID,
    payload: dict,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> AiAgent:
    return service.update_operational_config(
        db,
        company_id=current_user.company_id,
        agent_id=agent_id,
        payload=payload,
    )


@router.post("/agents/{agent_id}/operational-config/publish", response_model=AiAgentRead)
def publish_operational_config(
    agent_id: UUID,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> AiAgent:
    return service.publish_operational_config_for_agent(
        db,
        company_id=current_user.company_id,
        agent_id=agent_id,
    )


@router.post("/agents/{agent_id}/operational-config/simulate", response_model=AiOperationalSimulationResponse)
def simulate_operational_config(
    agent_id: UUID,
    payload: AiOperationalSimulationRequest,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> AiOperationalSimulationResponse:
    return service.simulate_operational_config(
        db,
        company_id=current_user.company_id,
        agent_id=agent_id,
        message=payload.message,
        operational_config=payload.operational_config,
    )


@router.post("/classify", response_model=IntentClassifyResponse)
def classify_message(payload: IntentClassifyRequest) -> IntentClassifyResponse:
    return service.classify_message(payload.message)


@router.get("/faqs", response_model=list[AiFaqEntryRead])
def list_faq_entries(
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> list[AiFaqEntry]:
    return service.list_faq_entries(db, company_id=current_user.company_id)


@router.post("/faqs", response_model=AiFaqEntryRead, status_code=201)
def create_faq_entry(
    payload: AiFaqEntryCreate,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> AiFaqEntry:
    return service.create_faq_entry(db, company_id=current_user.company_id, payload=payload)


@router.put("/faqs/{faq_id}", response_model=AiFaqEntryRead)
def update_faq_entry(
    faq_id: UUID,
    payload: AiFaqEntryUpdate,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> AiFaqEntry:
    return service.update_faq_entry(db, company_id=current_user.company_id, faq_id=faq_id, payload=payload)


@router.delete("/faqs/{faq_id}", status_code=204)
def delete_faq_entry(
    faq_id: UUID,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> None:
    service.delete_faq_entry(db, company_id=current_user.company_id, faq_id=faq_id)


@router.post("/faqs/upload", response_model=AiFaqUploadResult)
async def upload_faq_entries(
    file: UploadFile = File(...),
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> AiFaqUploadResult:
    content = await file.read()
    filename = file.filename or "faq_upload.csv"
    return service.upload_faq_entries(
        db,
        company_id=current_user.company_id,
        filename=filename,
        content=content,
    )


@router.get("/tools/search-products", response_model=SearchProductsToolResponse)
def search_products(
    q: str = Query(min_length=1),
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> SearchProductsToolResponse:
    return search_products_tool(db, company_id=current_user.company_id, query=q)


@router.get("/tools/check-stock/{product_id}", response_model=CheckStockToolResponse)
def check_stock(
    product_id: UUID,
    quantity: int = Query(default=1, ge=1),
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> CheckStockToolResponse:
    return check_stock_tool(
        db, company_id=current_user.company_id, product_id=product_id, quantity=quantity
    )


@router.get("/interactive-templates", response_model=list[AiInteractiveTemplateRead])
def list_interactive_templates(
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> list:
    return service.list_interactive_templates(db, company_id=current_user.company_id)


@router.post("/interactive-templates", response_model=AiInteractiveTemplateRead, status_code=201)
def create_interactive_template(
    payload: AiInteractiveTemplateCreate,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> object:
    return service.create_interactive_template(db, company_id=current_user.company_id, payload=payload)


@router.put("/interactive-templates/{template_id}", response_model=AiInteractiveTemplateRead)
def update_interactive_template(
    template_id: UUID,
    payload: AiInteractiveTemplateUpdate,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> object:
    return service.update_interactive_template(
        db,
        company_id=current_user.company_id,
        template_id=template_id,
        payload=payload,
    )


@router.delete("/interactive-templates/{template_id}", status_code=204)
def delete_interactive_template(
    template_id: UUID,
    current_user: User = Depends(require_module_access("ai")),
    db: Session = Depends(get_db),
) -> None:
    service.delete_interactive_template(db, company_id=current_user.company_id, template_id=template_id)

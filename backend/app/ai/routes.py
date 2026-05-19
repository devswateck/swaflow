from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai import service
from app.ai.models import AiAgent
from app.ai.schemas import (
    AiAgentCreate,
    AiAgentRead,
    AiAgentUpdate,
    CheckStockToolResponse,
    IntentClassifyRequest,
    IntentClassifyResponse,
    SearchProductsToolResponse,
)
from app.ai.tools import check_stock_tool, search_products_tool
from app.auth.service import get_current_user
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/agents", response_model=list[AiAgentRead])
def list_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AiAgent]:
    return service.list_agents(db, company_id=current_user.company_id)


@router.post("/agents", response_model=AiAgentRead, status_code=201)
def create_agent(
    payload: AiAgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAgent:
    return service.create_agent(db, company_id=current_user.company_id, payload=payload)


@router.put("/agents/{agent_id}", response_model=AiAgentRead)
def update_agent(
    agent_id: UUID,
    payload: AiAgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAgent:
    return service.update_agent(
        db, company_id=current_user.company_id, agent_id=agent_id, payload=payload
    )


@router.post("/classify", response_model=IntentClassifyResponse)
def classify_message(payload: IntentClassifyRequest) -> IntentClassifyResponse:
    return service.classify_message(payload.message)


@router.get("/tools/search-products", response_model=SearchProductsToolResponse)
def search_products(
    q: str = Query(min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchProductsToolResponse:
    return search_products_tool(db, company_id=current_user.company_id, query=q)


@router.get("/tools/check-stock/{product_id}", response_model=CheckStockToolResponse)
def check_stock(
    product_id: UUID,
    quantity: int = Query(default=1, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckStockToolResponse:
    return check_stock_tool(
        db, company_id=current_user.company_id, product_id=product_id, quantity=quantity
    )


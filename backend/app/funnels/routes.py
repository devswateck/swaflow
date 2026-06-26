from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import require_module_access
from app.core.database import get_db
from app.core.schemas import MessageResponse
from app.funnels import service
from app.funnels.models import SalesFunnel
from app.funnels.schemas import FunnelCreate, FunnelRead, FunnelUpdate
from app.users.models import User

router = APIRouter(prefix="/funnels", tags=["funnels"])


@router.get("", response_model=list[FunnelRead])
def list_funnels(
    current_user: User = Depends(require_module_access("funnels")),
    db: Session = Depends(get_db),
) -> list[SalesFunnel]:
    return service.list_funnels(db, company_id=current_user.company_id)


@router.post("", response_model=FunnelRead, status_code=201)
def create_funnel(
    payload: FunnelCreate,
    current_user: User = Depends(require_module_access("funnels")),
    db: Session = Depends(get_db),
) -> SalesFunnel:
    return service.create_funnel(db, company_id=current_user.company_id, payload=payload)


@router.put("/{funnel_id}", response_model=FunnelRead)
def update_funnel(
    funnel_id: UUID,
    payload: FunnelUpdate,
    current_user: User = Depends(require_module_access("funnels")),
    db: Session = Depends(get_db),
) -> SalesFunnel:
    return service.update_funnel(
        db, company_id=current_user.company_id, funnel_id=funnel_id, payload=payload
    )


@router.delete("/{funnel_id}", response_model=MessageResponse)
def delete_funnel(
    funnel_id: UUID,
    current_user: User = Depends(require_module_access("funnels")),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service.delete_funnel(db, company_id=current_user.company_id, funnel_id=funnel_id)
    return MessageResponse(detail="Funnel eliminado")

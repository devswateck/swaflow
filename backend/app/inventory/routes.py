from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.core.database import get_db
from app.inventory import service
from app.inventory.models import Inventory
from app.inventory.schemas import InventoryAdjustment, InventoryRead, InventoryUpdate
from app.users.models import User

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryRead])
def list_inventory(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Inventory]:
    return service.list_inventory(db, company_id=current_user.company_id, limit=limit, offset=offset)


@router.put("/{product_id}", response_model=InventoryRead)
def upsert_inventory(
    product_id: UUID,
    payload: InventoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Inventory:
    return service.upsert_inventory(
        db, company_id=current_user.company_id, product_id=product_id, payload=payload
    )


@router.post("/{product_id}/adjust", response_model=InventoryRead)
def adjust_inventory(
    product_id: UUID,
    payload: InventoryAdjustment,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Inventory:
    return service.adjust_inventory(
        db, company_id=current_user.company_id, product_id=product_id, payload=payload
    )


from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.core.database import get_db
from app.core.schemas import MessageResponse
from app.products import service
from app.products.models import Product
from app.products.schemas import ProductCreate, ProductRead, ProductUpdate
from app.users.models import User

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductRead])
def list_products(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Product]:
    return service.list_products(
        db,
        company_id=current_user.company_id,
        limit=limit,
        offset=offset,
        query=q,
        include_inactive=include_inactive,
    )


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Product:
    return service.create_product(db, company_id=current_user.company_id, payload=payload)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Product:
    return service.get_product(db, company_id=current_user.company_id, product_id=product_id)


@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Product:
    return service.update_product(
        db, company_id=current_user.company_id, product_id=product_id, payload=payload
    )


@router.delete("/{product_id}", response_model=MessageResponse)
def delete_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service.deactivate_product(db, company_id=current_user.company_id, product_id=product_id)
    return MessageResponse(detail="Product deactivated")


from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.products.models import Product
from app.products.schemas import ProductCreate, ProductUpdate


def list_products(
    db: Session,
    *,
    company_id: UUID,
    limit: int,
    offset: int,
    query: str | None = None,
    include_inactive: bool = False,
) -> list[Product]:
    stmt = select(Product).where(Product.company_id == company_id)
    if not include_inactive:
        stmt = stmt.where(Product.status == "active")
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
    return list(db.scalars(stmt.order_by(Product.created_at.desc()).limit(limit).offset(offset)))


def search_active_products(db: Session, *, company_id: UUID, query: str, limit: int = 10) -> list[Product]:
    return list_products(
        db,
        company_id=company_id,
        limit=limit,
        offset=0,
        query=query,
        include_inactive=False,
    )


def get_product(db: Session, *, company_id: UUID, product_id: UUID) -> Product:
    product = db.scalar(select(Product).where(Product.company_id == company_id, Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def create_product(db: Session, *, company_id: UUID, payload: ProductCreate) -> Product:
    product = Product(
        company_id=company_id,
        name=payload.name,
        description=payload.description,
        sku=payload.sku,
        price=payload.price,
        currency=payload.currency,
        whatsapp_catalog_id=payload.whatsapp_catalog_id,
        whatsapp_product_retailer_id=payload.whatsapp_product_retailer_id,
        metadata_json=payload.metadata,
    )
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists") from None
    db.refresh(product)
    return product


def update_product(
    db: Session, *, company_id: UUID, product_id: UUID, payload: ProductUpdate
) -> Product:
    product = get_product(db, company_id=company_id, product_id=product_id)
    data = payload.model_dump(exclude_unset=True)
    if "metadata" in data:
        data["metadata_json"] = data.pop("metadata")
    for field, value in data.items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists") from None
    db.refresh(product)
    return product


def deactivate_product(db: Session, *, company_id: UUID, product_id: UUID) -> None:
    product = get_product(db, company_id=company_id, product_id=product_id)
    product.status = "inactive"
    db.commit()

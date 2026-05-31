from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.inventory.models import Inventory
from app.inventory.schemas import InventoryAdjustment, InventoryUpdate
from app.products.models import Product
from app.products.service import get_product


def ensure_inventory_for_products(db: Session, *, company_id: UUID) -> int:
    product_ids = set(
        db.scalars(select(Product.id).where(Product.company_id == company_id))
    )
    if not product_ids:
        return 0

    existing_product_ids = set(
        db.scalars(
            select(Inventory.product_id).where(
                Inventory.company_id == company_id,
                Inventory.product_id.in_(product_ids),
            )
        )
    )
    missing_product_ids = product_ids - existing_product_ids
    db.add_all(
        Inventory(company_id=company_id, product_id=product_id)
        for product_id in missing_product_ids
    )
    return len(missing_product_ids)


def list_inventory(db: Session, *, company_id: UUID, limit: int, offset: int) -> list[Inventory]:
    if ensure_inventory_for_products(db, company_id=company_id):
        db.commit()
    return list(
        db.scalars(
            select(Inventory)
            .where(Inventory.company_id == company_id)
            .order_by(Inventory.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


def get_inventory_by_product(db: Session, *, company_id: UUID, product_id: UUID) -> Inventory:
    inventory = db.scalar(
        select(Inventory).where(
            Inventory.company_id == company_id,
            Inventory.product_id == product_id,
        )
    )
    if inventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    return inventory


def upsert_inventory(
    db: Session, *, company_id: UUID, product_id: UUID, payload: InventoryUpdate
) -> Inventory:
    get_product(db, company_id=company_id, product_id=product_id)
    inventory = db.scalar(
        select(Inventory).where(
            Inventory.company_id == company_id,
            Inventory.product_id == product_id,
        )
    )
    if inventory is None:
        inventory = Inventory(company_id=company_id, product_id=product_id)
        db.add(inventory)
    inventory.quantity_available = payload.quantity_available
    inventory.quantity_reserved = payload.quantity_reserved
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory already exists") from None
    db.refresh(inventory)
    return inventory


def adjust_inventory(
    db: Session, *, company_id: UUID, product_id: UUID, payload: InventoryAdjustment
) -> Inventory:
    inventory = get_inventory_by_product(db, company_id=company_id, product_id=product_id)
    next_available = inventory.quantity_available + payload.delta_available
    next_reserved = inventory.quantity_reserved + payload.delta_reserved
    if next_available < 0 or next_reserved < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Inventory quantities cannot be negative",
        )
    inventory.quantity_available = next_available
    inventory.quantity_reserved = next_reserved
    db.commit()
    db.refresh(inventory)
    return inventory


def available_units(inventory: Inventory) -> int:
    return inventory.quantity_available - inventory.quantity_reserved

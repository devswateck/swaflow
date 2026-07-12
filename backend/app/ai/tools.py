from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.schemas import (
    CheckStockToolResponse,
    ProductToolRead,
    SearchProductsToolResponse,
)
from app.inventory.service import available_units, get_inventory_by_product
from app.orders.schemas import OrderCreate
from app.orders.service import create_order, generate_payment_link
from app.products.service import (
    get_product,
    is_meta_synced_product,
    search_meta_synced_products,
)


def search_products_tool(
    db: Session, *, company_id: UUID, query: str
) -> SearchProductsToolResponse:
    products = search_meta_synced_products(db, company_id=company_id, query=query)
    result: list[ProductToolRead] = []
    for product in products:
        try:
            inventory = get_inventory_by_product(db, company_id=company_id, product_id=product.id)
            is_available = available_units(inventory) > 0
        except HTTPException:
            is_available = False
        result.append(
            ProductToolRead(
                id=product.id,
                name=product.name,
                price=product.price,
                currency=product.currency,
                available=is_available,
            )
        )
    return SearchProductsToolResponse(products=result)


def check_stock_tool(
    db: Session, *, company_id: UUID, product_id: UUID, quantity: int
) -> CheckStockToolResponse:
    if quantity < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Quantity must be greater than zero",
        )
    product = get_product(db, company_id=company_id, product_id=product_id)
    if not is_meta_synced_product(product):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    inventory = get_inventory_by_product(db, company_id=company_id, product_id=product_id)
    return CheckStockToolResponse(
        available=available_units(inventory) >= quantity,
        quantity_available=available_units(inventory),
    )


def create_order_tool(db: Session, *, company_id: UUID, payload: OrderCreate):
    return create_order(db, company_id=company_id, payload=payload)


def generate_payment_link_tool(db: Session, *, company_id: UUID, order_id: UUID):
    return generate_payment_link(db, company_id=company_id, order_id=order_id)

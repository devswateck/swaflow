"""orders idempotency key

Revision ID: 20260704_0021
Revises: 20260702_0020
Create Date: 2026-07-04 00:21:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260704_0021"
down_revision = "20260702_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )

    bind = op.get_bind()
    orders = sa.table(
        "orders",
        sa.column("id", sa.Uuid()),
        sa.column("idempotency_key", sa.String(length=255)),
    )
    rows = bind.execute(
        sa.select(orders.c.id).where(orders.c.idempotency_key.is_(None))
    ).all()
    for (order_id,) in rows:
        bind.execute(
            orders.update()
            .where(orders.c.id == order_id)
            .values(idempotency_key=f"legacy:{order_id}")
        )

    op.alter_column(
        "orders",
        "idempotency_key",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_orders_company_idempotency_key",
        "orders",
        ["company_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_orders_company_idempotency_key", "orders", type_="unique")
    op.drop_column("orders", "idempotency_key")

"""products whatsapp mapping

Revision ID: 20260527_0003
Revises: 20260527_0002
Create Date: 2026-05-27 00:03:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260527_0003"
down_revision = "20260527_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("whatsapp_catalog_id", sa.String(length=100), nullable=True))
    op.add_column(
        "products", sa.Column("whatsapp_product_retailer_id", sa.String(length=200), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("products", "whatsapp_product_retailer_id")
    op.drop_column("products", "whatsapp_catalog_id")


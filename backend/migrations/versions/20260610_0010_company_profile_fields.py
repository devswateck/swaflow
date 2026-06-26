"""company profile fields

Revision ID: 20260610_0010
Revises: 20260601_0009
Create Date: 2026-06-10 00:10:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260610_0010"
down_revision = "20260601_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("contact_email", sa.String(length=200), nullable=True))
    op.add_column("companies", sa.Column("contact_phone", sa.String(length=50), nullable=True))
    op.add_column("companies", sa.Column("currency", sa.String(length=10), nullable=True))
    op.add_column("companies", sa.Column("timezone", sa.String(length=64), nullable=True))
    op.add_column("companies", sa.Column("business_mode", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "business_mode")
    op.drop_column("companies", "timezone")
    op.drop_column("companies", "currency")
    op.drop_column("companies", "contact_phone")
    op.drop_column("companies", "contact_email")

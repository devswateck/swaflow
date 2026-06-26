"""company branding visual assets

Revision ID: 20260610_0011
Revises: 20260610_0010
Create Date: 2026-06-10 01:11:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260610_0011"
down_revision = "20260610_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("logo_url", sa.String(length=2048), nullable=True))
    op.add_column("companies", sa.Column("banner_url", sa.String(length=2048), nullable=True))
    op.add_column("companies", sa.Column("profile_url", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "profile_url")
    op.drop_column("companies", "banner_url")
    op.drop_column("companies", "logo_url")

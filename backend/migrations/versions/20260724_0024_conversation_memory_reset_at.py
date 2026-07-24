"""conversation memory reset at

Revision ID: 20260724_0024
Revises: 20260715_0023
Create Date: 2026-07-24 00:24:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_0024"
down_revision = "20260715_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("memory_reset_after_message_id", sa.Uuid(), nullable=True))
    op.add_column("conversations", sa.Column("memory_reset_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "memory_reset_after_message_id")
    op.drop_column("conversations", "memory_reset_at")

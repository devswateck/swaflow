"""appointment calendar sync tracking

Revision ID: 20260629_0017
Revises: 20260625_0016
Create Date: 2026-06-29 00:17:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260629_0017"
down_revision = "20260625_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("calendar_sync_status", sa.String(length=30), nullable=True))
    op.add_column("appointments", sa.Column("calendar_sync_error", sa.Text(), nullable=True))
    op.add_column(
        "appointments",
        sa.Column("calendar_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("calendar_sync_obsolete_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("appointments", "calendar_sync_obsolete_at")
    op.drop_column("appointments", "calendar_synced_at")
    op.drop_column("appointments", "calendar_sync_error")
    op.drop_column("appointments", "calendar_sync_status")

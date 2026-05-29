"""ai agent conversation objective

Revision ID: 20260528_0006
Revises: 20260528_0005
Create Date: 2026-05-28 17:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0006"
down_revision = "20260528_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_agents",
        sa.Column("conversation_objective", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("ai_agents", "conversation_objective")

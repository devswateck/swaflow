"""ai agent conversation guide

Revision ID: 20260601_0009
Revises: 20260601_0008
Create Date: 2026-06-01 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0009"
down_revision = "20260601_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_agents",
        sa.Column("conversation_guide", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("ai_agents", "conversation_guide")

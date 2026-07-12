"""conversation ai enabled

Revision ID: 20260702_0018
Revises: 20260629_0017
Create Date: 2026-07-02 00:18:00
"""
from alembic import op
import sqlalchemy as sa

revision = "20260702_0018"
down_revision = "20260629_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "ai_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "ai_enabled")

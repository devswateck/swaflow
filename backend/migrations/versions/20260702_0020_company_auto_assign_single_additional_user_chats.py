"""company auto assign single additional user chats

Revision ID: 20260702_0020
Revises: 20260702_0019
Create Date: 2026-07-02 00:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260702_0020"
down_revision = "20260702_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column(
            "auto_assign_single_additional_user_chats",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("companies", "auto_assign_single_additional_user_chats")

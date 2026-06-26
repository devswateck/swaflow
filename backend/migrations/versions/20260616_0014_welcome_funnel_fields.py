"""welcome funnel fields

Revision ID: 20260616_0014
Revises: 20260611_0013
Create Date: 2026-06-16 10:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260616_0014"
down_revision = "20260611_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_funnels", sa.Column("welcome_message", sa.Text(), nullable=True))
    op.add_column("sales_funnels", sa.Column("capture_fields", sa.JSON(), nullable=True))
    op.add_column("sales_funnels", sa.Column("assignment_criteria", sa.Text(), nullable=True))
    op.execute(
        sa.text("UPDATE sales_funnels SET capture_fields = '[]' WHERE capture_fields IS NULL")
    )
    with op.batch_alter_table("sales_funnels") as batch_op:
        batch_op.alter_column(
            "capture_fields",
            existing_type=sa.JSON(),
            nullable=False,
        )


def downgrade() -> None:
    op.drop_column("sales_funnels", "assignment_criteria")
    op.drop_column("sales_funnels", "capture_fields")
    op.drop_column("sales_funnels", "welcome_message")

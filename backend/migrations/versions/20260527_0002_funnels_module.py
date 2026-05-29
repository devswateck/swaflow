"""funnels module

Revision ID: 20260527_0002
Revises: 20260518_0001
Create Date: 2026-05-27 00:02:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260527_0002"
down_revision = "20260518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sales_funnels",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "name", name="uq_sales_funnels_company_name"),
    )
    op.create_index("ix_sales_funnels_company_id", "sales_funnels", ["company_id"])

    op.create_table(
        "sales_funnel_steps",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("funnel_id", sa.Uuid(), sa.ForeignKey("sales_funnels.id"), nullable=False),
        sa.Column("position", sa.Integer(), server_default="1", nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("prompt", sa.Text(), server_default="", nullable=False),
        sa.Column("objectives", sa.JSON(), nullable=False),
        sa.Column("transition_criteria", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "funnel_id", "position", name="uq_sales_funnel_steps_position"),
    )
    op.create_index("ix_sales_funnel_steps_company_id", "sales_funnel_steps", ["company_id"])
    op.create_index("ix_sales_funnel_steps_funnel_id", "sales_funnel_steps", ["funnel_id"])

    op.add_column("conversations", sa.Column("funnel_id", sa.Uuid(), nullable=True))
    op.add_column("conversations", sa.Column("funnel_step_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_conversations_funnel_id_sales_funnels",
        "conversations",
        "sales_funnels",
        ["funnel_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_conversations_funnel_step_id_sales_funnel_steps",
        "conversations",
        "sales_funnel_steps",
        ["funnel_step_id"],
        ["id"],
    )
    op.create_index("ix_conversations_funnel_id", "conversations", ["funnel_id"])
    op.create_index("ix_conversations_funnel_step_id", "conversations", ["funnel_step_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_funnel_step_id", table_name="conversations")
    op.drop_index("ix_conversations_funnel_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_funnel_step_id_sales_funnel_steps", "conversations", type_="foreignkey"
    )
    op.drop_constraint("fk_conversations_funnel_id_sales_funnels", "conversations", type_="foreignkey")
    op.drop_column("conversations", "funnel_step_id")
    op.drop_column("conversations", "funnel_id")

    op.drop_index("ix_sales_funnel_steps_funnel_id", table_name="sales_funnel_steps")
    op.drop_index("ix_sales_funnel_steps_company_id", table_name="sales_funnel_steps")
    op.drop_table("sales_funnel_steps")

    op.drop_index("ix_sales_funnels_company_id", table_name="sales_funnels")
    op.drop_table("sales_funnels")

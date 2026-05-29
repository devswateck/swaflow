"""ai interactive templates

Revision ID: 20260528_0004
Revises: 20260527_0003
Create Date: 2026-05-28 09:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0004"
down_revision = "20260527_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_interactive_templates",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("action_key", sa.String(length=120), nullable=False),
        sa.Column("template_type", sa.String(length=20), nullable=False, server_default="buttons"),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("footer_text", sa.String(length=60), nullable=True),
        sa.Column("button_text", sa.String(length=20), nullable=True),
        sa.Column("section_title", sa.String(length=24), nullable=True),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_interactive_templates_company_id",
        "ai_interactive_templates",
        ["company_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_interactive_templates_company_id", table_name="ai_interactive_templates")
    op.drop_table("ai_interactive_templates")

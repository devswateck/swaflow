"""ai faq entries and security rules

Revision ID: 20260528_0005
Revises: 20260528_0004
Create Date: 2026-05-28 16:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0005"
down_revision = "20260528_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_agents",
        sa.Column("security_rules", sa.Text(), nullable=False, server_default=""),
    )

    op.create_table(
        "ai_faq_entries",
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_faq_entries_company_id", "ai_faq_entries", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_faq_entries_company_id", table_name="ai_faq_entries")
    op.drop_table("ai_faq_entries")
    op.drop_column("ai_agents", "security_rules")

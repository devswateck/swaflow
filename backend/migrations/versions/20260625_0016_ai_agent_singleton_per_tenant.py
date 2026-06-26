"""ai agent singleton per tenant

Revision ID: 20260625_0016
Revises: 20260624_0015
Create Date: 2026-06-25 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_0016"
down_revision = "20260624_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE duplicate
            FROM ai_agents AS duplicate
            INNER JOIN ai_agents AS keeper
                ON duplicate.company_id = keeper.company_id
                AND (
                    duplicate.updated_at < keeper.updated_at
                    OR (
                        duplicate.updated_at = keeper.updated_at
                        AND duplicate.id < keeper.id
                    )
                )
            """
        )
    )
    op.create_unique_constraint(
        "uq_ai_agents_company",
        "ai_agents",
        ["company_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_ai_agents_company", "ai_agents", type_="unique")

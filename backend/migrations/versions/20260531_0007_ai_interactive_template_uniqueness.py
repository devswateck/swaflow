"""ai interactive template uniqueness

Revision ID: 20260531_0007
Revises: 20260528_0006
Create Date: 2026-05-31 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260531_0007"
down_revision = "20260528_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Older manually inserted rows can contain MySQL zero dates, which Pydantic
    # cannot serialize. Repair them before exposing the library in the UI.
    op.execute(
        sa.text(
            """
            UPDATE ai_interactive_templates
            SET created_at = CURRENT_TIMESTAMP
            WHERE CAST(created_at AS CHAR) = '0000-00-00 00:00:00'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE ai_interactive_templates
            SET updated_at = CURRENT_TIMESTAMP
            WHERE CAST(updated_at AS CHAR) = '0000-00-00 00:00:00'
            """
        )
    )

    # Keep the most recently updated definition for each tenant/action key.
    op.execute(
        sa.text(
            """
            DELETE duplicate
            FROM ai_interactive_templates AS duplicate
            INNER JOIN ai_interactive_templates AS keeper
                ON duplicate.company_id = keeper.company_id
                AND duplicate.action_key = keeper.action_key
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
        "uq_ai_interactive_templates_company_action",
        "ai_interactive_templates",
        ["company_id", "action_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_ai_interactive_templates_company_action",
        "ai_interactive_templates",
        type_="unique",
    )

"""ai interactive trigger rules

Revision ID: 20260601_0008
Revises: 20260531_0007
Create Date: 2026-06-01 00:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0008"
down_revision = "20260531_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_interactive_templates",
        sa.Column("usage_instruction", sa.Text(), nullable=True),
    )
    op.add_column(
        "ai_interactive_templates",
        sa.Column("trigger_mode", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "ai_interactive_templates",
        sa.Column("trigger_fields", sa.JSON(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE ai_interactive_templates
            SET usage_instruction = '',
                trigger_mode = 'ai_decides',
                trigger_fields = '[]'
            WHERE usage_instruction IS NULL
               OR trigger_mode IS NULL
               OR trigger_fields IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE ai_interactive_templates
            SET usage_instruction = 'Enviar despues de capturar nombre, email y ciudad del cliente.',
                trigger_mode = 'after_capture',
                trigger_fields = '["nombre", "email", "ciudad"]'
            WHERE action_key = 'menu_principal'
            """
        )
    )
    op.alter_column(
        "ai_interactive_templates",
        "usage_instruction",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        "ai_interactive_templates",
        "trigger_mode",
        existing_type=sa.String(length=30),
        nullable=False,
    )
    op.alter_column(
        "ai_interactive_templates",
        "trigger_fields",
        existing_type=sa.JSON(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("ai_interactive_templates", "trigger_fields")
    op.drop_column("ai_interactive_templates", "trigger_mode")
    op.drop_column("ai_interactive_templates", "usage_instruction")

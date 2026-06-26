"""user module permissions

Revision ID: 20260610_0012
Revises: 20260610_0011
Create Date: 2026-06-10 01:12:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260610_0012"
down_revision = "20260610_0011"
branch_labels = None
depends_on = None

SAFE_ACCESS_JSON = (
    '{"dashboard": true, "inbox": true, "products": true, "inventory": true, "orders": true, '
    '"appointments": true, "whatsapp": false, "ai": false, "funnels": false, '
    '"integrations": false, "settings": false}'
)
FULL_ACCESS_JSON = (
    '{"dashboard": true, "inbox": true, "products": true, "inventory": true, "orders": true, '
    '"appointments": true, "whatsapp": true, "ai": true, "funnels": true, '
    '"integrations": true, "settings": true}'
)


def upgrade() -> None:
    op.add_column("users", sa.Column("module_permissions", sa.JSON(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE users SET module_permissions = '"
            + FULL_ACCESS_JSON
            + "' WHERE role IN ('owner', 'admin', 'superadmin') AND module_permissions IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE users SET module_permissions = '"
            + SAFE_ACCESS_JSON
            + "' WHERE role NOT IN ('owner', 'admin', 'superadmin') AND module_permissions IS NULL"
        )
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "module_permissions",
            existing_type=sa.JSON(),
            nullable=False,
        )


def downgrade() -> None:
    op.drop_column("users", "module_permissions")

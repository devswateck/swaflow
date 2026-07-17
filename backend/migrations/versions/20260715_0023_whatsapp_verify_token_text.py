"""store whatsapp verify token as text

Revision ID: 20260715_0023
Revises: 20260713_0022
Create Date: 2026-07-15 00:23:00.000000
"""

from alembic import op
from cryptography.fernet import InvalidToken
import sqlalchemy as sa

from app.core.crypto import decrypt_secret, encrypt_secret


revision = "20260715_0023"
down_revision = "20260713_0022"
branch_labels = None
depends_on = None


def _backfill_verify_tokens(bind) -> None:
    metadata = sa.MetaData()
    whatsapp_accounts = sa.Table("whatsapp_accounts", metadata, autoload_with=bind)
    rows = bind.execute(sa.select(whatsapp_accounts.c.id, whatsapp_accounts.c.verify_token)).all()
    for row_id, verify_token in rows:
        if not verify_token:
            continue
        try:
            decrypt_secret(verify_token)
            continue
        except InvalidToken:
            bind.execute(
                sa.update(whatsapp_accounts)
                .where(whatsapp_accounts.c.id == row_id)
                .values(verify_token=encrypt_secret(verify_token))
            )


def upgrade() -> None:
    with op.batch_alter_table("whatsapp_accounts") as batch_op:
        batch_op.alter_column(
            "verify_token",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=False,
        )
    _backfill_verify_tokens(op.get_bind())


def downgrade() -> None:
    raise RuntimeError("Unsafe downgrade: whatsapp verify_token may exceed VARCHAR(255)")

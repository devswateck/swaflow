"""normalize contact phones to digits only

Revision ID: 20260702_0019
Revises: 20260702_0018
Create Date: 2026-07-02 00:19:00.000000
"""

from alembic import op
from sqlalchemy import select

from app.contacts.models import Contact


# revision identifiers, used by Alembic.
revision = "20260702_0019"
down_revision = "20260702_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    def _normalize_phone(phone: str) -> str:
        return "".join(char for char in phone if char.isdigit())

    rows = bind.execute(select(Contact.id, Contact.phone)).all()
    for contact_id, phone in rows:
        normalized_phone = _normalize_phone(phone or "")
        if normalized_phone and normalized_phone != phone:
            bind.execute(
                Contact.__table__.update()
                .where(Contact.id == contact_id)
                .values(phone=normalized_phone)
            )


def downgrade() -> None:
    pass

"""welcome funnel system key

Revision ID: 20260624_0015
Revises: 20260616_0014
Create Date: 2026-06-24 00:15:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260624_0015"
down_revision = "20260616_0014"
branch_labels = None
depends_on = None

WELCOME_FUNNEL_SYSTEM_KEY = "welcome"
WELCOME_FUNNEL_STEPS = ["bienvenida", "captura_inicial", "clasificacion_comercial"]
WELCOME_FUNNEL_MESSAGE = (
    "Hola, gracias por escribir. Soy el asistente de Swaflow. "
    "Para ayudarte mejor, cuentame tu nombre, correo y ciudad."
)
WELCOME_CAPTURE_FIELDS = ["Nombre", "Correo", "Ciudad"]
WELCOME_ASSIGNMENT_CRITERIA = "Conversaciones nuevas o sin clasificacion comercial previa"


def _normalize_capture_fields(value):
    return list(value) if isinstance(value, list) else []


def _is_likely_welcome_funnel(row, steps_by_funnel_id: dict) -> bool:
    step_codes = [step["code"] for step in steps_by_funnel_id.get(row["id"], [])]
    return step_codes == WELCOME_FUNNEL_STEPS


def _has_exact_welcome_signature(row, steps_by_funnel_id: dict) -> bool:
    if not _is_likely_welcome_funnel(row, steps_by_funnel_id):
        return False
    return (
        row["welcome_message"] == WELCOME_FUNNEL_MESSAGE
        and _normalize_capture_fields(row["capture_fields"]) == WELCOME_CAPTURE_FIELDS
        and row["assignment_criteria"] == WELCOME_ASSIGNMENT_CRITERIA
    )


def _backfill_company_welcome_funnel(connection, *, company_id):
    funnels = list(
        connection.execute(
            sa.text(
                """
                SELECT id, name, description, welcome_message, capture_fields, assignment_criteria, is_default
                FROM sales_funnels
                WHERE company_id = :company_id
                ORDER BY created_at ASC
                """
            ),
            {"company_id": company_id},
        ).mappings()
    )
    if not funnels:
        return
    steps = list(
        connection.execute(
            sa.text(
                """
                SELECT funnel_id, code
                FROM sales_funnel_steps
                WHERE company_id = :company_id
                ORDER BY position ASC
                """
            ),
            {"company_id": company_id},
        ).mappings()
    )
    steps_by_funnel_id: dict[str, list[dict]] = {}
    for step in steps:
        steps_by_funnel_id.setdefault(str(step["funnel_id"]), []).append(step)

    exact_candidates = [row for row in funnels if _has_exact_welcome_signature(row, steps_by_funnel_id)]
    if len(exact_candidates) != 1:
        return
    chosen = exact_candidates[0]

    connection.execute(
        sa.text("UPDATE sales_funnels SET system_key = :system_key WHERE id = :id"),
        {"system_key": WELCOME_FUNNEL_SYSTEM_KEY, "id": chosen["id"]},
    )


def upgrade() -> None:
    op.add_column("sales_funnels", sa.Column("system_key", sa.String(length=60), nullable=True))

    connection = op.get_bind()
    company_ids = [
        row[0]
        for row in connection.execute(
            sa.text("SELECT DISTINCT company_id FROM sales_funnels")
        )
    ]
    for company_id in company_ids:
        _backfill_company_welcome_funnel(connection, company_id=company_id)

    with op.batch_alter_table("sales_funnels") as batch_op:
        batch_op.create_unique_constraint(
            "uq_sales_funnels_company_system_key",
            ["company_id", "system_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("sales_funnels") as batch_op:
        batch_op.drop_constraint(
            "uq_sales_funnels_company_system_key",
            type_="unique",
        )
    op.drop_column("sales_funnels", "system_key")

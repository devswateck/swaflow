"""dashboard performance indexes

Revision ID: 20260713_0022
Revises: 20260704_0021
Create Date: 2026-07-13 00:22:00.000000
"""

from alembic import op


revision = "20260713_0022"
down_revision = "20260704_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_conversations_company_created_at",
        "conversations",
        ["company_id", "created_at"],
    )
    op.create_index(
        "ix_conversations_company_last_message_at",
        "conversations",
        ["company_id", "last_message_at"],
    )
    op.create_index(
        "ix_conversations_company_assigned_user_status",
        "conversations",
        ["company_id", "assigned_user_id", "status"],
    )
    op.create_index(
        "ix_conversations_company_funnel_id_funnel_step_id",
        "conversations",
        ["company_id", "funnel_id", "funnel_step_id"],
    )
    op.create_index(
        "ix_messages_company_created_at",
        "messages",
        ["company_id", "created_at"],
    )
    op.create_index(
        "ix_orders_company_created_at",
        "orders",
        ["company_id", "created_at"],
    )
    op.create_index(
        "ix_orders_company_status_created_at",
        "orders",
        ["company_id", "status", "created_at"],
    )
    op.create_index(
        "ix_orders_company_conversation_id",
        "orders",
        ["company_id", "conversation_id"],
    )
    op.create_index(
        "ix_order_items_company_product_order_id",
        "order_items",
        ["company_id", "product_id", "order_id"],
    )
    op.create_index(
        "ix_appointments_company_scheduled_at",
        "appointments",
        ["company_id", "scheduled_at"],
    )
    op.create_index(
        "ix_appointments_company_assigned_user_scheduled_at",
        "appointments",
        ["company_id", "assigned_user_id", "scheduled_at"],
    )
    op.create_index(
        "ix_appointments_company_conversation_id",
        "appointments",
        ["company_id", "conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_appointments_company_conversation_id", table_name="appointments")
    op.drop_index("ix_order_items_company_product_order_id", table_name="order_items")
    op.drop_index("ix_appointments_company_assigned_user_scheduled_at", table_name="appointments")
    op.drop_index("ix_appointments_company_scheduled_at", table_name="appointments")
    op.drop_index("ix_orders_company_conversation_id", table_name="orders")
    op.drop_index("ix_orders_company_status_created_at", table_name="orders")
    op.drop_index("ix_orders_company_created_at", table_name="orders")
    op.drop_index("ix_messages_company_created_at", table_name="messages")
    op.drop_index("ix_conversations_company_funnel_id_funnel_step_id", table_name="conversations")
    op.drop_index("ix_conversations_company_assigned_user_status", table_name="conversations")
    op.drop_index("ix_conversations_company_last_message_at", table_name="conversations")
    op.drop_index("ix_conversations_company_created_at", table_name="conversations")

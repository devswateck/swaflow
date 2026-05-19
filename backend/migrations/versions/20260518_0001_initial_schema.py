"""initial schema

Revision ID: 20260518_0001
Revises:
Create Date: 2026-05-18 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "20260518_0001"
down_revision = None
branch_labels = None
depends_on = None


def uuid_pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True, nullable=False)


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def tenant_column() -> sa.Column:
    return sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "companies",
        uuid_pk(),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        *timestamps(),
    )

    op.create_table(
        "users",
        uuid_pk(),
        tenant_column(),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=50), server_default="agent", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        *timestamps(),
        sa.UniqueConstraint("company_id", "email", name="uq_users_company_email"),
    )
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "whatsapp_accounts",
        uuid_pk(),
        tenant_column(),
        sa.Column("phone_number_id", sa.String(length=100), nullable=False),
        sa.Column("business_account_id", sa.String(length=100), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("verify_token", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        *timestamps(),
    )
    op.create_index("ix_whatsapp_accounts_company_id", "whatsapp_accounts", ["company_id"])
    op.create_index("ix_whatsapp_accounts_phone_number_id", "whatsapp_accounts", ["phone_number_id"])

    op.create_table(
        "contacts",
        uuid_pk(),
        tenant_column(),
        sa.Column("name", sa.String(length=150), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("source", sa.String(length=50), server_default="whatsapp", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("company_id", "phone", name="uq_contacts_company_phone"),
    )
    op.create_index("ix_contacts_company_id", "contacts", ["company_id"])

    op.create_table(
        "products",
        uuid_pk(),
        tenant_column(),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="COP", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("company_id", "sku", name="uq_products_company_sku"),
    )
    op.create_index("ix_products_company_id", "products", ["company_id"])

    op.create_table(
        "conversations",
        uuid_pk(),
        tenant_column(),
        sa.Column("contact_id", sa.Uuid(), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("channel", sa.String(length=50), server_default="whatsapp", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="open", nullable=False),
        sa.Column("assigned_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_conversations_company_id", "conversations", ["company_id"])
    op.create_index("ix_conversations_contact_id", "conversations", ["contact_id"])

    op.create_table(
        "inventory",
        uuid_pk(),
        tenant_column(),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity_available", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quantity_reserved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "product_id", name="uq_inventory_company_product"),
    )
    op.create_index("ix_inventory_company_id", "inventory", ["company_id"])
    op.create_index("ix_inventory_product_id", "inventory", ["product_id"])

    op.create_table(
        "messages",
        uuid_pk(),
        tenant_column(),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("external_message_id", sa.String(length=150), nullable=True),
        sa.Column("sender_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("message_type", sa.String(length=50), server_default="text", nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_messages_company_id", "messages", ["company_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_external_message_id", "messages", ["external_message_id"])

    op.create_table(
        "orders",
        uuid_pk(),
        tenant_column(),
        sa.Column("contact_id", sa.Uuid(), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("total", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="COP", nullable=False),
        sa.Column("payment_provider", sa.String(length=50), nullable=True),
        sa.Column("payment_reference", sa.String(length=150), nullable=True),
        sa.Column("payment_link", sa.Text(), nullable=True),
        sa.Column("payment_status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_orders_company_id", "orders", ["company_id"])
    op.create_index("ix_orders_contact_id", "orders", ["contact_id"])
    op.create_index("ix_orders_payment_reference", "orders", ["payment_reference"])

    op.create_table(
        "appointments",
        uuid_pk(),
        tenant_column(),
        sa.Column("contact_id", sa.Uuid(), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("assigned_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default="30", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="scheduled", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("external_calendar_event_id", sa.String(length=255), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_appointments_company_id", "appointments", ["company_id"])
    op.create_index("ix_appointments_contact_id", "appointments", ["contact_id"])

    op.create_table(
        "ai_agents",
        uuid_pk(),
        tenant_column(),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(length=100), nullable=True),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_ai_agents_company_id", "ai_agents", ["company_id"])

    op.create_table(
        "company_integrations",
        uuid_pk(),
        tenant_column(),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        *timestamps(),
    )
    op.create_index("ix_company_integrations_company_id", "company_integrations", ["company_id"])

    op.create_table(
        "outbound_webhooks",
        uuid_pk(),
        tenant_column(),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("secret_token", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_outbound_webhooks_company_id", "outbound_webhooks", ["company_id"])

    op.create_table(
        "events",
        uuid_pk(),
        tenant_column(),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_events_company_id", "events", ["company_id"])
    op.create_index("ix_events_event_type", "events", ["event_type"])

    op.create_table(
        "order_items",
        uuid_pk(),
        tenant_column(),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_order_items_company_id", "order_items", ["company_id"])
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_index("ix_order_items_company_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_company_id", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_outbound_webhooks_company_id", table_name="outbound_webhooks")
    op.drop_table("outbound_webhooks")
    op.drop_index("ix_company_integrations_company_id", table_name="company_integrations")
    op.drop_table("company_integrations")
    op.drop_index("ix_ai_agents_company_id", table_name="ai_agents")
    op.drop_table("ai_agents")
    op.drop_index("ix_appointments_contact_id", table_name="appointments")
    op.drop_index("ix_appointments_company_id", table_name="appointments")
    op.drop_table("appointments")
    op.drop_index("ix_orders_payment_reference", table_name="orders")
    op.drop_index("ix_orders_contact_id", table_name="orders")
    op.drop_index("ix_orders_company_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_messages_external_message_id", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_index("ix_messages_company_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_inventory_product_id", table_name="inventory")
    op.drop_index("ix_inventory_company_id", table_name="inventory")
    op.drop_table("inventory")
    op.drop_index("ix_conversations_contact_id", table_name="conversations")
    op.drop_index("ix_conversations_company_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_products_company_id", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_contacts_company_id", table_name="contacts")
    op.drop_table("contacts")
    op.drop_index("ix_whatsapp_accounts_phone_number_id", table_name="whatsapp_accounts")
    op.drop_index("ix_whatsapp_accounts_company_id", table_name="whatsapp_accounts")
    op.drop_table("whatsapp_accounts")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_company_id", table_name="users")
    op.drop_table("users")
    op.drop_table("companies")

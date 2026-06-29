from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.audit.service import record_audit
from app.ai.models import AiAgent, AiFaqEntry, AiInteractiveTemplate
from app.companies.models import Company
from app.contacts.models import Contact
from app.conversations.models import Conversation
from app.events.models import Event
from app.funnels.models import SalesFunnel, SalesFunnelStep
from app.integrations.models import CompanyIntegration, OutboundWebhook
from app.inventory.models import Inventory
from app.messages.models import Message
from app.orders.models import Order, OrderItem
from app.appointments.models import Appointment
from app.products.models import Product
from app.whatsapp.models import WhatsAppAccount
from app.users.models import User

_SENSITIVE_KEY_FRAGMENTS = (
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
    "signature",
    "api_key",
    "client_secret",
)


@dataclass(slots=True)
class ExportPackage:
    filename: str
    content: bytes
    row_counts: dict[str, int]


def _stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


def _render_pipe_file(headers: list[str], rows: list[list[object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="|", lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_stringify(value) for value in row])
    return buffer.getvalue()


def _sanitize_json_blob(value: dict | None) -> dict:
    if not isinstance(value, dict):
        return {}
    sanitized: dict = {}
    for key, child in value.items():
        key_text = str(key).lower()
        if any(fragment in key_text or key_text.endswith(fragment) for fragment in _SENSITIVE_KEY_FRAGMENTS):
            continue
        if isinstance(child, dict):
            sanitized[key] = _sanitize_json_blob(child)
        elif isinstance(child, list):
            sanitized[key] = [
                _sanitize_json_blob(item) if isinstance(item, dict) else item
                for item in child
            ]
        else:
            sanitized[key] = child
    return sanitized


def _company_rows(company: Company) -> list[list[object]]:
    return [
        [
            company.id,
            company.name,
            company.status,
            company.contact_email,
            company.contact_phone,
            company.currency,
            company.timezone,
            company.business_mode,
            company.logo_url,
            company.banner_url,
            company.profile_url,
            company.created_at,
            company.updated_at,
        ]
    ]


def _user_rows(users: list[User]) -> list[list[object]]:
    return [
        [
            user.id,
            user.name,
            user.email,
            user.role,
            user.status,
            json.dumps(user.module_permissions or {}, ensure_ascii=False, sort_keys=True),
            user.created_at,
            user.updated_at,
        ]
        for user in users
    ]


def _contact_rows(contacts: list[Contact]) -> list[list[object]]:
    return [
        [
            contact.id,
            contact.name,
            contact.phone,
            contact.email,
            contact.source,
            contact.status,
            json.dumps(_sanitize_json_blob(contact.metadata_json), ensure_ascii=False, sort_keys=True),
            contact.created_at,
            contact.updated_at,
        ]
        for contact in contacts
    ]


def _conversation_rows(conversations: list[Conversation]) -> list[list[object]]:
    return [
        [
            conversation.id,
            conversation.contact_id,
            conversation.channel,
            conversation.status,
            conversation.assigned_user_id,
            conversation.funnel_id,
            conversation.funnel_step_id,
            conversation.current_step,
            conversation.last_message_at,
            conversation.unread_count,
            conversation.created_at,
            conversation.updated_at,
        ]
        for conversation in conversations
    ]


def _message_rows(messages: list[Message]) -> list[list[object]]:
    return [
        [
            message.id,
            message.conversation_id,
            message.external_message_id,
            message.sender_type,
            message.message_type,
            message.content,
            json.dumps(_sanitize_json_blob(message.metadata_json), ensure_ascii=False, sort_keys=True),
            message.created_at,
        ]
        for message in messages
    ]


def _product_rows(products: list[Product]) -> list[list[object]]:
    return [
        [
            product.id,
            product.name,
            product.description,
            product.sku,
            product.price,
            product.currency,
            product.status,
            product.whatsapp_catalog_id,
            product.whatsapp_product_retailer_id,
            json.dumps(_sanitize_json_blob(product.metadata_json), ensure_ascii=False, sort_keys=True),
            product.created_at,
            product.updated_at,
        ]
        for product in products
    ]


def _ai_agent_rows(agents: list[AiAgent]) -> list[list[object]]:
    return [
        [
            agent.id,
            agent.name,
            agent.system_prompt,
            agent.conversation_objective,
            agent.conversation_guide,
            agent.security_rules,
            agent.tone,
            json.dumps(_sanitize_json_blob(agent.rules), ensure_ascii=False, sort_keys=True),
            agent.active,
            agent.created_at,
            agent.updated_at,
        ]
        for agent in agents
    ]


def _ai_faq_rows(entries: list[AiFaqEntry]) -> list[list[object]]:
    return [
        [
            entry.id,
            entry.question,
            entry.answer,
            entry.active,
            entry.created_at,
            entry.updated_at,
        ]
        for entry in entries
    ]


def _ai_template_rows(templates: list[AiInteractiveTemplate]) -> list[list[object]]:
    return [
        [
            template.id,
            template.name,
            template.action_key,
            template.template_type,
            template.body_text,
            template.footer_text,
            template.button_text,
            template.section_title,
            json.dumps(_sanitize_json_blob(template.options), ensure_ascii=False, sort_keys=True),
            template.usage_instruction,
            template.trigger_mode,
            json.dumps(template.trigger_fields or [], ensure_ascii=False, sort_keys=True),
            template.active,
            template.created_at,
            template.updated_at,
        ]
        for template in templates
    ]


def _funnel_rows(funnels: list[SalesFunnel]) -> list[list[object]]:
    return [
        [
            funnel.id,
            funnel.name,
            funnel.system_key,
            funnel.description,
            funnel.status,
            funnel.is_default,
            funnel.welcome_message,
            json.dumps(funnel.capture_fields or [], ensure_ascii=False, sort_keys=True),
            funnel.assignment_criteria,
            funnel.created_at,
            funnel.updated_at,
        ]
        for funnel in funnels
    ]


def _funnel_step_rows(steps: list[SalesFunnelStep]) -> list[list[object]]:
    return [
        [
            step.id,
            step.funnel_id,
            step.position,
            step.name,
            step.code,
            step.prompt,
            json.dumps(step.objectives or [], ensure_ascii=False, sort_keys=True),
            step.transition_criteria,
            step.status,
            json.dumps(_sanitize_json_blob(step.config), ensure_ascii=False, sort_keys=True),
            step.created_at,
            step.updated_at,
        ]
        for step in steps
    ]


def _whatsapp_account_rows(accounts: list[WhatsAppAccount]) -> list[list[object]]:
    return [
        [
            account.id,
            account.phone_number_id,
            account.business_account_id,
            account.status,
            bool(account.access_token_encrypted),
            bool(account.verify_token),
            account.created_at,
            account.updated_at,
        ]
        for account in accounts
    ]


def _inventory_rows(inventory_rows: list[Inventory]) -> list[list[object]]:
    return [
        [
            inventory.id,
            inventory.product_id,
            inventory.quantity_available,
            inventory.quantity_reserved,
            inventory.updated_at,
        ]
        for inventory in inventory_rows
    ]


def _order_rows(orders: list[Order]) -> list[list[object]]:
    return [
        [
            order.id,
            order.contact_id,
            order.conversation_id,
            order.status,
            order.total,
            order.currency,
            order.payment_provider,
            order.payment_reference,
            order.payment_status,
            json.dumps(_sanitize_json_blob(order.metadata_json), ensure_ascii=False, sort_keys=True),
            order.created_at,
            order.updated_at,
        ]
        for order in orders
    ]


def _order_item_rows(order_items: list[OrderItem]) -> list[list[object]]:
    return [
        [
            item.id,
            item.order_id,
            item.product_id,
            item.quantity,
            item.unit_price,
            item.total,
            item.created_at,
        ]
        for item in order_items
    ]


def _appointment_rows(appointments: list[Appointment]) -> list[list[object]]:
    return [
        [
            appointment.id,
            appointment.contact_id,
            appointment.conversation_id,
            appointment.assigned_user_id,
            appointment.scheduled_at,
            appointment.duration_minutes,
            appointment.status,
            appointment.notes,
            appointment.external_calendar_event_id,
            appointment.calendar_sync_status,
            appointment.calendar_synced_at,
            appointment.calendar_sync_obsolete_at,
            appointment.created_at,
            appointment.updated_at,
        ]
        for appointment in appointments
    ]


def _event_rows(events: list[Event]) -> list[list[object]]:
    return [
        [
            event.id,
            event.event_type,
            event.status,
            event.processed_at,
            json.dumps(_sanitize_json_blob(event.payload), ensure_ascii=False, sort_keys=True),
            event.created_at,
        ]
        for event in events
    ]


def _audit_rows(logs: list[AuditLog]) -> list[list[object]]:
    return [
        [
            log.id,
            log.actor_user_id,
            log.actor_role,
            log.action,
            log.entity_type,
            log.entity_id,
            log.summary,
            json.dumps(_sanitize_json_blob(log.metadata_json), ensure_ascii=False, sort_keys=True),
            log.created_at,
        ]
        for log in logs
    ]


def _integration_rows(integrations: list[CompanyIntegration]) -> list[list[object]]:
    return [
        [
            integration.id,
            integration.type,
            integration.status,
            integration.credentials_configured,
            json.dumps(_sanitize_json_blob(integration.config), ensure_ascii=False, sort_keys=True),
            integration.created_at,
            integration.updated_at,
        ]
        for integration in integrations
    ]


def _outbound_webhook_rows(webhooks: list[OutboundWebhook]) -> list[list[object]]:
    return [
        [
            webhook.id,
            webhook.event_type,
            webhook.target_url,
            webhook.active,
            webhook.secret_configured,
            webhook.created_at,
            webhook.updated_at,
        ]
        for webhook in webhooks
    ]


def _write_file(zip_file: zipfile.ZipFile, filename: str, headers: list[str], rows: list[list[object]]) -> int:
    content = _render_pipe_file(headers, rows)
    zip_file.writestr(filename, content)
    return len(rows)


def build_tenant_export(
    db: Session,
    *,
    company_id: UUID,
    actor_user: User | None = None,
) -> ExportPackage:
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    users = list(
        db.scalars(select(User).where(User.company_id == company_id).order_by(User.created_at.asc()))
    )
    contacts = list(
        db.scalars(
            select(Contact).where(Contact.company_id == company_id).order_by(Contact.created_at.asc())
        )
    )
    conversations = list(
        db.scalars(
            select(Conversation)
            .where(Conversation.company_id == company_id)
            .order_by(Conversation.created_at.asc())
        )
    )
    messages = list(
        db.scalars(
            select(Message).where(Message.company_id == company_id).order_by(Message.created_at.asc())
        )
    )
    products = list(
        db.scalars(
            select(Product).where(Product.company_id == company_id).order_by(Product.created_at.asc())
        )
    )
    ai_agents = list(
        db.scalars(select(AiAgent).where(AiAgent.company_id == company_id).order_by(AiAgent.created_at.asc()))
    )
    ai_faq_entries = list(
        db.scalars(
            select(AiFaqEntry).where(AiFaqEntry.company_id == company_id).order_by(AiFaqEntry.created_at.asc())
        )
    )
    ai_templates = list(
        db.scalars(
            select(AiInteractiveTemplate)
            .where(AiInteractiveTemplate.company_id == company_id)
            .order_by(AiInteractiveTemplate.created_at.asc())
        )
    )
    funnels = list(
        db.scalars(
            select(SalesFunnel).where(SalesFunnel.company_id == company_id).order_by(SalesFunnel.created_at.asc())
        )
    )
    funnel_steps = list(
        db.scalars(
            select(SalesFunnelStep)
            .where(SalesFunnelStep.company_id == company_id)
            .order_by(SalesFunnelStep.created_at.asc())
        )
    )
    inventory_rows = list(
        db.scalars(
            select(Inventory).where(Inventory.company_id == company_id).order_by(Inventory.updated_at.asc())
        )
    )
    orders = list(
        db.scalars(select(Order).where(Order.company_id == company_id).order_by(Order.created_at.asc()))
    )
    order_items = list(
        db.scalars(
            select(OrderItem)
            .where(OrderItem.company_id == company_id)
            .order_by(OrderItem.created_at.asc())
        )
    )
    appointments = list(
        db.scalars(
            select(Appointment)
            .where(Appointment.company_id == company_id)
            .order_by(Appointment.scheduled_at.asc(), Appointment.created_at.asc())
        )
    )
    events = list(
        db.scalars(select(Event).where(Event.company_id == company_id).order_by(Event.created_at.asc()))
    )
    audit_logs = list(
        db.scalars(
            select(AuditLog).where(AuditLog.company_id == company_id).order_by(AuditLog.created_at.asc())
        )
    )
    integrations = list(
        db.scalars(
            select(CompanyIntegration)
            .where(CompanyIntegration.company_id == company_id)
            .order_by(CompanyIntegration.created_at.asc())
        )
    )
    webhooks = list(
        db.scalars(
            select(OutboundWebhook)
            .where(OutboundWebhook.company_id == company_id)
            .order_by(OutboundWebhook.created_at.asc())
        )
    )
    whatsapp_accounts = list(
        db.scalars(
            select(WhatsAppAccount)
            .where(WhatsAppAccount.company_id == company_id)
            .order_by(WhatsAppAccount.created_at.asc())
        )
    )

    archive = io.BytesIO()
    row_counts: dict[str, int] = {}
    created_at = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"swaflow-tenant-export-{company.id}-{created_at}.zip"

    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        row_counts["company"] = _write_file(
            zip_file,
            "company.txt",
            [
                "id",
                "name",
                "status",
                "contact_email",
                "contact_phone",
                "currency",
                "timezone",
                "business_mode",
                "logo_url",
                "banner_url",
                "profile_url",
                "created_at",
                "updated_at",
            ],
            _company_rows(company),
        )
        row_counts["users"] = _write_file(
            zip_file,
            "users.txt",
            ["id", "name", "email", "role", "status", "module_permissions_json", "created_at", "updated_at"],
            _user_rows(users),
        )
        row_counts["contacts"] = _write_file(
            zip_file,
            "contacts.txt",
            ["id", "name", "phone", "email", "source", "status", "metadata_json", "created_at", "updated_at"],
            _contact_rows(contacts),
        )
        row_counts["conversations"] = _write_file(
            zip_file,
            "conversations.txt",
            [
                "id",
                "contact_id",
                "channel",
                "status",
                "assigned_user_id",
                "funnel_id",
                "funnel_step_id",
                "current_step",
                "last_message_at",
                "unread_count",
                "created_at",
                "updated_at",
            ],
            _conversation_rows(conversations),
        )
        row_counts["messages"] = _write_file(
            zip_file,
            "messages.txt",
            [
                "id",
                "conversation_id",
                "external_message_id",
                "sender_type",
                "message_type",
                "content",
                "metadata_json",
                "created_at",
            ],
            _message_rows(messages),
        )
        row_counts["products"] = _write_file(
            zip_file,
            "products.txt",
            [
                "id",
                "name",
                "description",
                "sku",
                "price",
                "currency",
                "status",
                "whatsapp_catalog_id",
                "whatsapp_product_retailer_id",
                "metadata_json",
                "created_at",
                "updated_at",
            ],
            _product_rows(products),
        )
        row_counts["ai_agents"] = _write_file(
            zip_file,
            "ai_agents.txt",
            [
                "id",
                "name",
                "system_prompt",
                "conversation_objective",
                "conversation_guide",
                "security_rules",
                "tone",
                "rules_json",
                "active",
                "created_at",
                "updated_at",
            ],
            _ai_agent_rows(ai_agents),
        )
        row_counts["ai_faq_entries"] = _write_file(
            zip_file,
            "ai_faq_entries.txt",
            ["id", "question", "answer", "active", "created_at", "updated_at"],
            _ai_faq_rows(ai_faq_entries),
        )
        row_counts["ai_interactive_templates"] = _write_file(
            zip_file,
            "ai_interactive_templates.txt",
            [
                "id",
                "name",
                "action_key",
                "template_type",
                "body_text",
                "footer_text",
                "button_text",
                "section_title",
                "options_json",
                "usage_instruction",
                "trigger_mode",
                "trigger_fields_json",
                "active",
                "created_at",
                "updated_at",
            ],
            _ai_template_rows(ai_templates),
        )
        row_counts["sales_funnels"] = _write_file(
            zip_file,
            "sales_funnels.txt",
            [
                "id",
                "name",
                "system_key",
                "description",
                "status",
                "is_default",
                "welcome_message",
                "capture_fields_json",
                "assignment_criteria",
                "created_at",
                "updated_at",
            ],
            _funnel_rows(funnels),
        )
        row_counts["sales_funnel_steps"] = _write_file(
            zip_file,
            "sales_funnel_steps.txt",
            [
                "id",
                "funnel_id",
                "position",
                "name",
                "code",
                "prompt",
                "objectives_json",
                "transition_criteria",
                "status",
                "config_json",
                "created_at",
                "updated_at",
            ],
            _funnel_step_rows(funnel_steps),
        )
        row_counts["whatsapp_accounts"] = _write_file(
            zip_file,
            "whatsapp_accounts.txt",
            [
                "id",
                "phone_number_id",
                "business_account_id",
                "status",
                "access_token_configured",
                "verify_token_configured",
                "created_at",
                "updated_at",
            ],
            _whatsapp_account_rows(whatsapp_accounts),
        )
        row_counts["inventory"] = _write_file(
            zip_file,
            "inventory.txt",
            ["id", "product_id", "quantity_available", "quantity_reserved", "updated_at"],
            _inventory_rows(inventory_rows),
        )
        row_counts["orders"] = _write_file(
            zip_file,
            "orders.txt",
            [
                "id",
                "contact_id",
                "conversation_id",
                "status",
                "total",
                "currency",
                "payment_provider",
                "payment_reference",
                "payment_status",
                "metadata_json",
                "created_at",
                "updated_at",
            ],
            _order_rows(orders),
        )
        row_counts["order_items"] = _write_file(
            zip_file,
            "order_items.txt",
            ["id", "order_id", "product_id", "quantity", "unit_price", "total", "created_at"],
            _order_item_rows(order_items),
        )
        row_counts["appointments"] = _write_file(
            zip_file,
            "appointments.txt",
            [
                "id",
                "contact_id",
                "conversation_id",
                "assigned_user_id",
                "scheduled_at",
                "duration_minutes",
                "status",
                "notes",
                "external_calendar_event_id",
                "calendar_sync_status",
                "calendar_synced_at",
                "calendar_sync_obsolete_at",
                "created_at",
                "updated_at",
            ],
            _appointment_rows(appointments),
        )
        row_counts["events"] = _write_file(
            zip_file,
            "events.txt",
            ["id", "event_type", "status", "processed_at", "payload_json", "created_at"],
            _event_rows(events),
        )
        row_counts["audit_logs"] = _write_file(
            zip_file,
            "audit_logs.txt",
            [
                "id",
                "actor_user_id",
                "actor_role",
                "action",
                "entity_type",
                "entity_id",
                "summary",
                "metadata_json",
                "created_at",
            ],
            _audit_rows(audit_logs),
        )
        row_counts["integrations"] = _write_file(
            zip_file,
            "integrations.txt",
            ["id", "type", "status", "credentials_configured", "config_json", "created_at", "updated_at"],
            _integration_rows(integrations),
        )
        row_counts["outbound_webhooks"] = _write_file(
            zip_file,
            "outbound_webhooks.txt",
            ["id", "event_type", "target_url", "active", "secret_configured", "created_at", "updated_at"],
            _outbound_webhook_rows(webhooks),
        )

    content = archive.getvalue()
    if actor_user is not None:
        try:
            record_audit(
                db,
                company_id=company.id,
                actor_user=actor_user,
                action="tenant.export_created",
                entity_type="company",
                entity_id=company.id,
                summary="Tenant export generated",
                metadata={
                    "filename": filename,
                    "module_count": len(row_counts),
                    "row_counts": row_counts,
                },
            )
            db.commit()
        except Exception:
            db.rollback()
    return ExportPackage(filename=filename, content=content, row_counts=row_counts)

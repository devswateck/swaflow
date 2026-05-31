from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contacts.models import Contact
from app.core.crypto import decrypt_secret
from app.integrations.models import CompanyIntegration
from app.orders.models import Order
from app.users.models import User


def _get_email_integration(db: Session, *, company_id) -> CompanyIntegration | None:
    return db.scalar(
        select(CompanyIntegration)
        .where(
            CompanyIntegration.company_id == company_id,
            CompanyIntegration.type == "email",
            CompanyIntegration.status == "active",
        )
        .order_by(CompanyIntegration.updated_at.desc())
    )


def _smtp_password(raw: str | None) -> str:
    if not raw:
        return ""
    decoded = decrypt_secret(raw)
    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError:
        return decoded
    if isinstance(parsed, dict):
        return str(parsed.get("password") or parsed.get("api_key") or "")
    return decoded


def _admin_emails(db: Session, *, company_id) -> list[str]:
    return list(
        db.scalars(
            select(User.email).where(
                User.company_id == company_id,
                User.role.in_(["owner", "admin"]),
                User.status == "active",
            )
        )
    )


def _send_smtp(
    *,
    integration: CompanyIntegration,
    recipients: Iterable[str],
    subject: str,
    body: str,
) -> None:
    config = integration.config if isinstance(integration.config, dict) else {}
    host = str(config.get("smtp_host") or "").strip()
    port = int(str(config.get("smtp_port") or "587").strip())
    from_email = str(config.get("from_email") or "").strip()
    from_name = str(config.get("from_name") or "SwaFlow").strip()
    reply_to = str(config.get("reply_to") or "").strip()
    username = str(config.get("smtp_username") or from_email).strip()
    password = _smtp_password(integration.credentials_encrypted)

    if not host or not from_email:
        return

    message = EmailMessage()
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = ", ".join(sorted(set(recipients)))
    message["Subject"] = subject
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)


def notify_order_paid(db: Session, *, order: Order) -> None:
    integration = _get_email_integration(db, company_id=order.company_id)
    if integration is None:
        return

    contact = db.get(Contact, order.contact_id)
    admin_emails = _admin_emails(db, company_id=order.company_id)
    recipients = [email for email in [contact.email if contact else None, *admin_emails] if email]
    if not recipients:
        return

    subject = f"Pago confirmado - Orden {str(order.id)[:8]}"
    body = (
        "Pago confirmado en SwaFlow.\n\n"
        f"Orden: {order.id}\n"
        f"Referencia: {order.payment_reference or '-'}\n"
        f"Total: {order.total} {order.currency}\n"
        f"Cliente: {(contact.name if contact else None) or '-'}\n"
        f"Correo cliente: {(contact.email if contact else None) or '-'}\n\n"
        "El equipo puede continuar con validacion, despacho o entrega segun el flujo definido."
    )
    _send_smtp(integration=integration, recipients=recipients, subject=subject, body=body)

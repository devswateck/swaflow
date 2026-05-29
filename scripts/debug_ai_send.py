import app.models
from sqlalchemy import select

from app.contacts.models import Contact
from app.conversations.models import Conversation
from app.core.database import SessionLocal
from app.messages.models import Message
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.service import _send_text_with_account


def main() -> None:
    db = SessionLocal()
    try:
        message = db.scalar(
            select(Message)
            .where(Message.sender_type == "customer", Message.content.is_not(None))
            .order_by(Message.created_at.desc())
        )
        if message is None:
            print("NO_CUSTOMER_MESSAGE")
            return

        conversation = db.scalar(
            select(Conversation).where(Conversation.id == message.conversation_id)
        )
        if conversation is None:
            print("NO_CONVERSATION")
            return

        contact = db.scalar(select(Contact).where(Contact.id == conversation.contact_id))
        if contact is None:
            print("NO_CONTACT")
            return

        account = db.scalar(
            select(WhatsAppAccount)
            .where(
                WhatsAppAccount.company_id == message.company_id,
                WhatsAppAccount.status == "active",
            )
            .order_by(WhatsAppAccount.created_at.desc())
        )
        if account is None:
            print("NO_WHATSAPP_ACCOUNT")
            return

        print("TO", contact.phone)
        print("ACCOUNT", account.phone_number_id)
        print("COMPANY", message.company_id)
        print("TEXT", message.content)
        try:
            response = _send_text_with_account(
                db,
                account=account,
                to=contact.phone,
                body="Prueba envio IA backend",
                source="ai_auto_reply_test",
            )
            print("SEND_OK", response.meta_message_id)
        except Exception as exc:  # noqa: BLE001
            print("SEND_ERR", exc.__class__.__name__, str(exc))
    finally:
        db.close()


if __name__ == "__main__":
    main()

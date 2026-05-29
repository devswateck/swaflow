from app.contacts.models import Contact
from app.conversations.models import Conversation
from app.db.session import SessionLocal
from app.events.models import Event
from app.messages.models import Message
from sqlalchemy import select


def main() -> None:
    phone_input = "3193187250"
    normalized = f"+57{phone_input}" if not phone_input.startswith("+") else phone_input
    alternates = {phone_input, normalized, f"57{phone_input}"}

    with SessionLocal() as db:
        contacts = list(db.scalars(select(Contact).where(Contact.phone.in_(alternates))))
        if not contacts:
            print("NO_CONTACT")
            return

        total_messages = 0
        total_conversations = 0
        total_events = 0

        for contact in contacts:
            conversations = list(
                db.scalars(
                    select(Conversation).where(
                        Conversation.contact_id == contact.id,
                        Conversation.company_id == contact.company_id,
                    )
                )
            )
            for conversation in conversations:
                messages = list(
                    db.scalars(
                        select(Message).where(
                            Message.conversation_id == conversation.id,
                            Message.company_id == conversation.company_id,
                        )
                    )
                )
                for message in messages:
                    db.delete(message)
                    total_messages += 1

                events = list(
                    db.scalars(select(Event).where(Event.company_id == conversation.company_id))
                )
                for event in events:
                    payload = event.payload if isinstance(event.payload, dict) else {}
                    if str(payload.get("conversation_id", "")) == str(conversation.id):
                        db.delete(event)
                        total_events += 1

                db.delete(conversation)
                total_conversations += 1

            db.delete(contact)

        db.commit()
        print(
            "DELETED contacts=%s conversations=%s messages=%s events=%s"
            % (len(contacts), total_conversations, total_messages, total_events)
        )


if __name__ == "__main__":
    main()

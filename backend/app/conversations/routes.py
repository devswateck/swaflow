from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user, require_module_access
from app.conversations import service
from app.conversations.models import Conversation
from app.conversations.schemas import (
    ConversationAssign,
    ConversationAppointmentIntentRead,
    ConversationCreate,
    ConversationDetailRead,
    ConversationFunnelAssign,
    ConversationListItemRead,
    ConversationRead,
    ConversationSendMessage,
)
from app.core.database import get_db
from app.messages.models import Message
from app.messages.schemas import MessageRead
from app.users.models import User

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationListItemRead])
def list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    funnel_id: UUID | None = None,
    funnel_step_id: UUID | None = None,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> list[dict]:
    conversations = service.list_conversations(
        db,
        company_id=current_user.company_id,
        limit=limit,
        offset=offset,
        status_filter=status,
        funnel_id=funnel_id,
        funnel_step_id=funnel_step_id,
    )
    return [
        service.conversation_to_inbox_item(db, conversation=conversation)
        for conversation in conversations
    ]


@router.post("", response_model=ConversationRead, status_code=201)
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.create_conversation(db, company_id=current_user.company_id, payload=payload)


@router.get("/{conversation_id}", response_model=ConversationDetailRead)
def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> dict:
    conversation = service.get_conversation(
        db, company_id=current_user.company_id, conversation_id=conversation_id
    )
    messages = service.get_conversation_messages(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        memory_reset_at=conversation.memory_reset_at,
    )
    events = service.get_conversation_events(
        db, company_id=current_user.company_id, conversation_id=conversation_id
    )
    return {
        **service.conversation_to_inbox_item(db, conversation=conversation),
        "messages": messages,
        "events": events,
    }


@router.post("/{conversation_id}/assign", response_model=ConversationRead)
def assign_conversation(
    conversation_id: UUID,
    payload: ConversationAssign,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.assign_conversation(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        assigned_user_id=payload.assigned_user_id,
        actor_user=current_user,
    )


@router.post("/{conversation_id}/assign-funnel", response_model=ConversationRead)
def assign_conversation_funnel(
    conversation_id: UUID,
    payload: ConversationFunnelAssign,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.assign_conversation_funnel(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        funnel_id=payload.funnel_id,
        funnel_step_id=payload.funnel_step_id,
        current_step=payload.current_step,
        actor_user=current_user,
    )


@router.post("/{conversation_id}/prepare-appointment", response_model=ConversationAppointmentIntentRead)
def prepare_conversation_appointment_intent(
    conversation_id: UUID,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> dict:
    return service.prepare_conversation_appointment_intent(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        actor_user=current_user,
    )


@router.get("/{conversation_id}/appointment-intent", response_model=ConversationAppointmentIntentRead)
def get_conversation_appointment_intent(
    conversation_id: UUID,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> dict:
    conversation = service.get_conversation(
        db, company_id=current_user.company_id, conversation_id=conversation_id
    )
    return service.get_conversation_appointment_intent(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        memory_reset_at=conversation.memory_reset_at,
        conversation=conversation,
    )


@router.post("/{conversation_id}/close", response_model=ConversationRead)
def close_conversation(
    conversation_id: UUID,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.close_conversation(
        db, company_id=current_user.company_id, conversation_id=conversation_id
    )


@router.post("/{conversation_id}/ai/pause", response_model=ConversationRead)
def pause_conversation_ai(
    conversation_id: UUID,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.set_conversation_ai_enabled(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        ai_enabled=False,
        actor_user=current_user,
    )


@router.post("/{conversation_id}/ai/resume", response_model=ConversationRead)
def resume_conversation_ai(
    conversation_id: UUID,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.set_conversation_ai_enabled(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        ai_enabled=True,
        actor_user=current_user,
    )


@router.post("/{conversation_id}/read", response_model=ConversationRead)
def mark_conversation_read(
    conversation_id: UUID,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.mark_conversation_read(
        db, company_id=current_user.company_id, conversation_id=conversation_id
    )


@router.post("/{conversation_id}/send-message", response_model=MessageRead)
def send_message(
    conversation_id: UUID,
    payload: ConversationSendMessage,
    current_user: User = Depends(require_module_access("inbox")),
    db: Session = Depends(get_db),
) -> Message:
    return service.append_message(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        sender_type="agent",
        content=payload.content,
        actor_user=current_user,
    )

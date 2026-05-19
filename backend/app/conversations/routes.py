from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.conversations import service
from app.conversations.models import Conversation
from app.conversations.schemas import (
    ConversationAssign,
    ConversationCreate,
    ConversationDetailRead,
    ConversationRead,
    ConversationSendMessage,
)
from app.core.database import get_db
from app.messages.models import Message
from app.messages.schemas import MessageRead
from app.users.models import User

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    return service.list_conversations(
        db,
        company_id=current_user.company_id,
        limit=limit,
        offset=offset,
        status_filter=status,
    )


@router.post("", response_model=ConversationRead, status_code=201)
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.create_conversation(db, company_id=current_user.company_id, payload=payload)


@router.get("/{conversation_id}", response_model=ConversationDetailRead)
def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conversation = service.get_conversation(
        db, company_id=current_user.company_id, conversation_id=conversation_id
    )
    messages = service.get_conversation_messages(
        db, company_id=current_user.company_id, conversation_id=conversation_id
    )
    return {**conversation.__dict__, "messages": messages}


@router.post("/{conversation_id}/assign", response_model=ConversationRead)
def assign_conversation(
    conversation_id: UUID,
    payload: ConversationAssign,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.assign_conversation(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        assigned_user_id=payload.assigned_user_id,
    )


@router.post("/{conversation_id}/close", response_model=ConversationRead)
def close_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Conversation:
    return service.close_conversation(
        db, company_id=current_user.company_id, conversation_id=conversation_id
    )


@router.post("/{conversation_id}/send-message", response_model=MessageRead)
def send_message(
    conversation_id: UUID,
    payload: ConversationSendMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    return service.append_message(
        db,
        company_id=current_user.company_id,
        conversation_id=conversation_id,
        sender_type="agent",
        content=payload.content,
    )


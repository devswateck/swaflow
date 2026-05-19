from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.intent_classifier import classify_intent
from app.ai.models import AiAgent
from app.ai.schemas import AiAgentCreate, AiAgentUpdate, IntentClassifyResponse


def list_agents(db: Session, *, company_id: UUID) -> list[AiAgent]:
    return list(
        db.scalars(
            select(AiAgent)
            .where(AiAgent.company_id == company_id)
            .order_by(AiAgent.created_at.desc())
        )
    )


def create_agent(db: Session, *, company_id: UUID, payload: AiAgentCreate) -> AiAgent:
    agent = AiAgent(
        company_id=company_id,
        name=payload.name,
        system_prompt=payload.system_prompt,
        tone=payload.tone,
        rules=payload.rules,
        active=payload.active,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def get_agent(db: Session, *, company_id: UUID, agent_id: UUID) -> AiAgent:
    agent = db.scalar(select(AiAgent).where(AiAgent.company_id == company_id, AiAgent.id == agent_id))
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI agent not found")
    return agent


def update_agent(
    db: Session, *, company_id: UUID, agent_id: UUID, payload: AiAgentUpdate
) -> AiAgent:
    agent = get_agent(db, company_id=company_id, agent_id=agent_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return agent


def classify_message(message: str) -> IntentClassifyResponse:
    return classify_intent(message)


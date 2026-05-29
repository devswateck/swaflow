from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.funnels.models import SalesFunnel, SalesFunnelStep
from app.funnels.schemas import FunnelCreate, FunnelStepWrite, FunnelUpdate


def _with_steps_stmt(company_id: UUID):
    return (
        select(SalesFunnel)
        .where(SalesFunnel.company_id == company_id)
        .options(selectinload(SalesFunnel.steps))
        .order_by(SalesFunnel.created_at.desc())
    )


def list_funnels(db: Session, *, company_id: UUID) -> list[SalesFunnel]:
    return list(db.scalars(_with_steps_stmt(company_id)))


def get_funnel(db: Session, *, company_id: UUID, funnel_id: UUID) -> SalesFunnel:
    funnel = db.scalar(
        _with_steps_stmt(company_id).where(SalesFunnel.id == funnel_id)
    )
    if funnel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel not found")
    return funnel


def _set_default_if_requested(
    db: Session, *, company_id: UUID, is_default: bool
) -> None:
    if not is_default:
        return
    existing_defaults = list(
        db.scalars(
            select(SalesFunnel).where(
                SalesFunnel.company_id == company_id, SalesFunnel.is_default.is_(True)
            )
        )
    )
    for item in existing_defaults:
        item.is_default = False


def _sync_steps(
    db: Session, *, company_id: UUID, funnel: SalesFunnel, steps: list[FunnelStepWrite]
) -> None:
    funnel.steps.clear()
    sorted_steps = sorted(steps, key=lambda step: step.position)
    for step in sorted_steps:
        funnel.steps.append(
            SalesFunnelStep(
                company_id=company_id,
                funnel_id=funnel.id,
                position=step.position,
                name=step.name,
                code=step.code,
                prompt=step.prompt,
                objectives=step.objectives,
                transition_criteria=step.transition_criteria,
                status=step.status,
                config=step.config,
            )
        )
    db.flush()


def create_funnel(db: Session, *, company_id: UUID, payload: FunnelCreate) -> SalesFunnel:
    _set_default_if_requested(db, company_id=company_id, is_default=payload.is_default)
    funnel = SalesFunnel(
        company_id=company_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        is_default=payload.is_default,
    )
    db.add(funnel)
    db.flush()
    _sync_steps(db, company_id=company_id, funnel=funnel, steps=payload.steps)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Funnel name already exists") from exc
    return get_funnel(db, company_id=company_id, funnel_id=funnel.id)


def update_funnel(
    db: Session, *, company_id: UUID, funnel_id: UUID, payload: FunnelUpdate
) -> SalesFunnel:
    funnel = get_funnel(db, company_id=company_id, funnel_id=funnel_id)
    data = payload.model_dump(exclude_unset=True)
    if "is_default" in data:
        _set_default_if_requested(
            db, company_id=company_id, is_default=bool(data["is_default"])
        )
    steps = data.pop("steps", None)
    for field, value in data.items():
        setattr(funnel, field, value)
    if steps is not None:
        _sync_steps(db, company_id=company_id, funnel=funnel, steps=steps)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Funnel name already exists") from exc
    return get_funnel(db, company_id=company_id, funnel_id=funnel.id)


def delete_funnel(db: Session, *, company_id: UUID, funnel_id: UUID) -> None:
    funnel = get_funnel(db, company_id=company_id, funnel_id=funnel_id)
    db.delete(funnel)
    db.commit()

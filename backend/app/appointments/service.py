import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment
from app.appointments.schemas import AppointmentCreate, AppointmentUpdate
from app.audit.service import record_audit_best_effort
from app.contacts.service import get_contact
from app.conversations.service import get_conversation
from app.events.service import create_event
from app.users.models import User
from app.integrations.calendar import sync_appointment_with_calendar

logger = logging.getLogger(__name__)


def _mark_calendar_sync_success(appointment: Appointment, sync_result) -> None:
    now = datetime.now(UTC)
    appointment.external_calendar_event_id = sync_result.external_event_id
    appointment.calendar_sync_status = "synced"
    appointment.calendar_sync_error = None
    appointment.calendar_sync_obsolete_at = None
    appointment.calendar_synced_at = now


def _mark_calendar_sync_failure(appointment: Appointment, reason: Exception) -> str:
    now = datetime.now(UTC)
    if appointment.external_calendar_event_id:
        status_value = "obsolete"
        appointment.calendar_sync_obsolete_at = now
    else:
        status_value = "failed"
        appointment.calendar_sync_obsolete_at = None
    appointment.calendar_sync_status = status_value
    appointment.calendar_sync_error = str(reason)
    return status_value


def list_appointments(
    db: Session, *, company_id: UUID, limit: int, offset: int
) -> list[Appointment]:
    return list(
        db.scalars(
            select(Appointment)
            .where(Appointment.company_id == company_id)
            .order_by(Appointment.scheduled_at.asc())
            .limit(limit)
            .offset(offset)
        )
    )


def get_appointment(db: Session, *, company_id: UUID, appointment_id: UUID) -> Appointment:
    appointment = db.scalar(
        select(Appointment).where(
            Appointment.company_id == company_id,
            Appointment.id == appointment_id,
        )
    )
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


def _validate_links(
    db: Session,
    *,
    company_id: UUID,
    contact_id: UUID | None = None,
    conversation_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
) -> None:
    if contact_id is not None:
        get_contact(db, company_id=company_id, contact_id=contact_id)
    if conversation_id is not None:
        get_conversation(db, company_id=company_id, conversation_id=conversation_id)
    if assigned_user_id is not None:
        user = db.scalar(select(User).where(User.company_id == company_id, User.id == assigned_user_id))
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


def create_appointment(
    db: Session,
    *,
    company_id: UUID,
    payload: AppointmentCreate,
    actor_user: User | None = None,
) -> Appointment:
    _validate_links(
        db,
        company_id=company_id,
        contact_id=payload.contact_id,
        conversation_id=payload.conversation_id,
        assigned_user_id=payload.assigned_user_id,
    )
    appointment = Appointment(
        company_id=company_id,
        contact_id=payload.contact_id,
        conversation_id=payload.conversation_id,
        assigned_user_id=payload.assigned_user_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
    )
    db.add(appointment)
    db.flush()
    create_event(
        db,
        company_id=company_id,
        event_type="appointment.created",
        payload={"appointment_id": str(appointment.id), "scheduled_at": appointment.scheduled_at.isoformat()},
    )
    db.commit()
    db.refresh(appointment)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="appointment.created",
        entity_type="appointment",
        entity_id=appointment.id,
        summary="Appointment created",
        metadata={
            "contact_id": str(appointment.contact_id),
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
            "scheduled_at": appointment.scheduled_at.isoformat(),
            "status": appointment.status,
        },
    )
    try:
        sync_result = sync_appointment_with_calendar(db, company_id=company_id, appointment=appointment)
    except Exception as exc:
        logger.warning(
            "Calendar sync failed for appointment create company_id=%s appointment_id=%s detail=%s",
            company_id,
            appointment.id,
            exc,
        )
        sync_status = _mark_calendar_sync_failure(appointment, exc)
        create_event(
            db,
            company_id=company_id,
            event_type="appointment.calendar_sync_failed",
            payload={
                "appointment_id": str(appointment.id),
                "reason": str(exc),
                "sync_status": sync_status,
                "external_calendar_event_id": appointment.external_calendar_event_id,
            },
        )
        db.commit()
        sync_result = None
    if sync_result is not None:
        _mark_calendar_sync_success(appointment, sync_result)
        create_event(
            db,
            company_id=company_id,
            event_type="appointment.calendar_synced",
            payload={
                "appointment_id": str(appointment.id),
                "provider": sync_result.raw.get("provider"),
                "external_calendar_event_id": sync_result.external_event_id,
                "sync_status": appointment.calendar_sync_status,
            },
        )
        db.commit()
        db.refresh(appointment)
    return appointment


def update_appointment(
    db: Session,
    *,
    company_id: UUID,
    appointment_id: UUID,
    payload: AppointmentUpdate,
    actor_user: User | None = None,
) -> Appointment:
    appointment = get_appointment(db, company_id=company_id, appointment_id=appointment_id)
    data = payload.model_dump(exclude_unset=True)
    _validate_links(db, company_id=company_id, assigned_user_id=data.get("assigned_user_id"))
    for field, value in data.items():
        setattr(appointment, field, value)
    db.commit()
    db.refresh(appointment)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="appointment.updated",
        entity_type="appointment",
        entity_id=appointment.id,
        summary="Appointment updated",
        metadata={
            "contact_id": str(appointment.contact_id),
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
            "status": appointment.status,
        },
    )
    try:
        sync_result = sync_appointment_with_calendar(db, company_id=company_id, appointment=appointment)
    except Exception as exc:
        logger.warning(
            "Calendar sync failed for appointment update company_id=%s appointment_id=%s detail=%s",
            company_id,
            appointment.id,
            exc,
        )
        sync_status = _mark_calendar_sync_failure(appointment, exc)
        create_event(
            db,
            company_id=company_id,
            event_type="appointment.calendar_sync_failed",
            payload={
                "appointment_id": str(appointment.id),
                "reason": str(exc),
                "sync_status": sync_status,
                "external_calendar_event_id": appointment.external_calendar_event_id,
            },
        )
        db.commit()
        sync_result = None
    if sync_result is not None:
        _mark_calendar_sync_success(appointment, sync_result)
        create_event(
            db,
            company_id=company_id,
            event_type="appointment.calendar_synced",
            payload={
                "appointment_id": str(appointment.id),
                "provider": sync_result.raw.get("provider"),
                "external_calendar_event_id": sync_result.external_event_id,
                "sync_status": appointment.calendar_sync_status,
            },
        )
        db.commit()
        db.refresh(appointment)
    return appointment


def cancel_appointment(
    db: Session,
    *,
    company_id: UUID,
    appointment_id: UUID,
    actor_user: User | None = None,
) -> Appointment:
    appointment = get_appointment(db, company_id=company_id, appointment_id=appointment_id)
    if appointment.status in {"cancelled", "completed", "no_show"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Appointment cannot be cancelled from its current status",
    )
    appointment.status = "cancelled"
    create_event(
        db,
        company_id=company_id,
        event_type="appointment.cancelled",
        payload={"appointment_id": str(appointment.id)},
    )
    db.commit()
    db.refresh(appointment)
    record_audit_best_effort(
        db,
        company_id=company_id,
        actor_user=actor_user,
        action="appointment.cancelled",
        entity_type="appointment",
        entity_id=appointment.id,
        summary="Appointment cancelled",
        metadata={
            "contact_id": str(appointment.contact_id),
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
        },
    )
    return appointment

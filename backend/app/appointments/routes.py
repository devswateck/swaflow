from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.appointments import service
from app.appointments.models import Appointment
from app.appointments.schemas import (
    AppointmentAvailabilityRead,
    AppointmentAvailabilityRequest,
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
)
from app.auth.service import require_module_access
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/availability", response_model=AppointmentAvailabilityRead)
def get_appointment_availability(
    payload: AppointmentAvailabilityRequest,
    current_user: User = Depends(require_module_access("appointments")),
    db: Session = Depends(get_db),
) -> AppointmentAvailabilityRead:
    return service.get_appointment_availability(
        db,
        company_id=current_user.company_id,
        payload=payload,
    )


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    focus_appointment_id: UUID | None = Query(default=None),
    current_user: User = Depends(require_module_access("appointments")),
    db: Session = Depends(get_db),
) -> list[Appointment]:
    return service.list_appointments(
        db,
        company_id=current_user.company_id,
        limit=limit,
        offset=offset,
        focus_appointment_id=focus_appointment_id,
    )


@router.post("", response_model=AppointmentRead, status_code=201)
def create_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(require_module_access("appointments")),
    db: Session = Depends(get_db),
) -> Appointment:
    return service.create_appointment(
        db,
        company_id=current_user.company_id,
        payload=payload,
        actor_user=current_user,
    )


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(
    appointment_id: UUID,
    current_user: User = Depends(require_module_access("appointments")),
    db: Session = Depends(get_db),
) -> Appointment:
    return service.get_appointment(
        db, company_id=current_user.company_id, appointment_id=appointment_id
    )


@router.put("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: UUID,
    payload: AppointmentUpdate,
    current_user: User = Depends(require_module_access("appointments")),
    db: Session = Depends(get_db),
) -> Appointment:
    return service.update_appointment(
        db,
        company_id=current_user.company_id,
        appointment_id=appointment_id,
        payload=payload,
        actor_user=current_user,
    )


@router.post("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(
    appointment_id: UUID,
    current_user: User = Depends(require_module_access("appointments")),
    db: Session = Depends(get_db),
) -> Appointment:
    return service.cancel_appointment(
        db,
        company_id=current_user.company_id,
        appointment_id=appointment_id,
        actor_user=current_user,
    )

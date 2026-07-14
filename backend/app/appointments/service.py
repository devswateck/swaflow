import logging
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment
from app.appointments.schemas import (
    AppointmentOperationalConfigRead,
    AppointmentOperationalConfigUpdate,
)
from app.appointments.schemas import (
    AppointmentAvailabilityOption,
    AppointmentAvailabilityRead,
    AppointmentAvailabilityRequest,
    AppointmentCreate,
    AppointmentUpdate,
)
from app.ai.models import AiAgent
from app.ai.operational import (
    build_operational_config,
    get_default_appointment_duration_minutes as get_operational_default_appointment_duration_minutes,
    get_effective_operational_section,
)
from app.audit.service import record_audit_best_effort
from app.companies.models import Company
from app.contacts.service import get_contact
from app.conversations.service import get_conversation
from app.events.service import create_event
from app.integrations.calendar import calendar_credentials_raw, get_calendar_adapter, normalize_calendar_config
from app.integrations.models import CompanyIntegration
from app.realtime import realtime_manager
from app.users.models import User
from app.integrations.calendar import sync_appointment_with_calendar

logger = logging.getLogger(__name__)

DEFAULT_APPOINTMENT_DURATION_MINUTES = 60
DEFAULT_AVAILABILITY_HORIZON_DAYS = 7
DEFAULT_AVAILABILITY_STEP_MINUTES = 15
MORNING_PERIOD_WINDOW = {"start": "08:00", "end": "12:00"}
AFTERNOON_PERIOD_WINDOW = {"start": "14:00", "end": "18:00"}
NON_BLOCKING_APPOINTMENT_STATUSES = {"cancelled", "completed", "no_show"}


def _normalize_timezone(timezone_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _parse_clock(value: str) -> time:
    hour_str, minute_str = value.split(":", 1)
    return time(hour=int(hour_str), minute=int(minute_str))


def _window_as_times(window: dict[str, str]) -> tuple[time, time]:
    return _parse_clock(window["start"]), _parse_clock(window["end"])


def _datetime_in_timezone(value: datetime, tzinfo: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).astimezone(tzinfo)
    return value.astimezone(tzinfo)


def _merge_busy_intervals(
    intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda interval: interval[0])
    merged: list[tuple[datetime, datetime]] = [ordered[0]]
    for current_start, current_end in ordered[1:]:
        previous_start, previous_end = merged[-1]
        if current_start <= previous_end:
            merged[-1] = (previous_start, max(previous_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged


def _slot_overlaps_busy(
    slot_start: datetime,
    slot_end: datetime,
    busy_intervals: list[tuple[datetime, datetime]],
) -> bool:
    for busy_start, busy_end in busy_intervals:
        if slot_start < busy_end and slot_end > busy_start:
            return True
    return False


def _get_company(db: Session, *, company_id: UUID) -> Company:
    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


def _get_company_operational_section(db: Session, *, company_id: UUID) -> tuple[dict, ZoneInfo]:
    company = _get_company(db, company_id=company_id)
    agent = db.scalar(
        select(AiAgent)
        .where(AiAgent.company_id == company_id)
        .order_by(AiAgent.updated_at.desc(), AiAgent.created_at.desc())
    )
    raw_rules = agent.rules if agent and isinstance(agent.rules, dict) else {}
    operational_config = build_operational_config(raw_rules, fallback_timezone=company.timezone)
    section = get_effective_operational_section(operational_config)
    schedule = section.get("schedule") if isinstance(section, dict) else {}
    timezone_name = company.timezone
    if isinstance(schedule, dict):
        timezone_name = str(schedule.get("timezone") or timezone_name or "UTC")
    return section, _normalize_timezone(timezone_name)


def _get_default_duration_minutes(section: dict) -> int:
    operational_config = {"draft": section, "published": section, "status": "draft", "version": 1}
    return get_operational_default_appointment_duration_minutes(operational_config)


def _preferred_window(period: str) -> dict[str, str]:
    if period == "afternoon":
        return dict(AFTERNOON_PERIOD_WINDOW)
    return dict(MORNING_PERIOD_WINDOW)


def _operational_window_for_date(
    section: dict,
    *,
    day: date,
    tzinfo: ZoneInfo,
) -> tuple[datetime, datetime] | None:
    schedule = section.get("schedule") if isinstance(section, dict) else {}
    if not isinstance(schedule, dict):
        schedule = {}
    window_key = "weekend" if day.weekday() >= 5 else "weekday"
    operational_window = schedule.get(window_key)
    if not isinstance(operational_window, dict):
        return None
    start_clock = _parse_clock(str(operational_window.get("start") or "08:00"))
    end_clock = _parse_clock(str(operational_window.get("end") or "18:00"))
    if end_clock <= start_clock:
        return None
    return (
        datetime.combine(day, start_clock, tzinfo=tzinfo),
        datetime.combine(day, end_clock, tzinfo=tzinfo),
    )


def _day_window_for_date(
    section: dict,
    *,
    day: date,
    preferred_period: str,
    tzinfo: ZoneInfo,
) -> tuple[datetime, datetime] | None:
    operational_window = _operational_window_for_date(section, day=day, tzinfo=tzinfo)
    if operational_window is None:
        return None
    preferred_window = _preferred_window(preferred_period)
    operational_start, operational_end = operational_window
    preferred_start = _parse_clock(preferred_window["start"])
    preferred_end = _parse_clock(preferred_window["end"])
    start_at = max(operational_start, datetime.combine(day, preferred_start, tzinfo=tzinfo))
    end_at = min(operational_end, datetime.combine(day, preferred_end, tzinfo=tzinfo))
    if end_at <= start_at:
        return None
    return start_at, end_at


def _collect_internal_busy_intervals(
    db: Session,
    *,
    company_id: UUID,
    start_at: datetime,
    end_at: datetime,
    tzinfo: ZoneInfo,
    ignore_appointment_id: UUID | None = None,
) -> list[tuple[datetime, datetime]]:
    appointments = list(
        db.scalars(
            select(Appointment)
            .where(
                Appointment.company_id == company_id,
                Appointment.scheduled_at >= start_at.astimezone(UTC),
                Appointment.scheduled_at < end_at.astimezone(UTC),
            )
            .order_by(Appointment.scheduled_at.asc(), Appointment.created_at.asc())
        )
    )
    intervals: list[tuple[datetime, datetime]] = []
    for appointment in appointments:
        if ignore_appointment_id is not None and appointment.id == ignore_appointment_id:
            continue
        if appointment.status in NON_BLOCKING_APPOINTMENT_STATUSES:
            continue
        appointment_start = _datetime_in_timezone(appointment.scheduled_at, tzinfo)
        appointment_end = appointment_start + timedelta(minutes=appointment.duration_minutes)
        intervals.append((appointment_start, appointment_end))
    for appointment in db.scalars(
        select(Appointment)
        .where(
            Appointment.company_id == company_id,
            Appointment.scheduled_at < start_at.astimezone(UTC),
        )
        .order_by(Appointment.scheduled_at.desc(), Appointment.created_at.desc())
    ):
        if ignore_appointment_id is not None and appointment.id == ignore_appointment_id:
            continue
        if appointment.status in NON_BLOCKING_APPOINTMENT_STATUSES:
            continue
        appointment_start = _datetime_in_timezone(appointment.scheduled_at, tzinfo)
        appointment_end = appointment_start + timedelta(minutes=appointment.duration_minutes)
        if appointment_end > start_at:
            intervals.append((appointment_start, appointment_end))
    return _merge_busy_intervals(intervals)


def _collect_calendar_busy_intervals(
    db: Session,
    *,
    company_id: UUID,
    start_at: datetime,
    end_at: datetime,
    tzinfo: ZoneInfo,
) -> tuple[list[tuple[datetime, datetime]], bool, str | None]:
    integration = db.scalar(
        select(CompanyIntegration)
        .where(
            CompanyIntegration.company_id == company_id,
            CompanyIntegration.type == "calendar",
            CompanyIntegration.status == "active",
        )
        .order_by(CompanyIntegration.updated_at.desc())
    )
    if integration is None:
        return [], False, None

    try:
        config = normalize_calendar_config(integration.config)
        credentials = calendar_credentials_raw(integration)
        adapter = get_calendar_adapter(config.get("provider"))
        busy_intervals = adapter.fetch_busy_intervals(
            company_id=company_id,
            time_min=start_at.astimezone(tzinfo),
            time_max=end_at.astimezone(tzinfo),
            config=config,
            credentials_raw=credentials,
        )
        normalized = [
            (
                _datetime_in_timezone(interval.start, tzinfo),
                _datetime_in_timezone(interval.end, tzinfo),
            )
            for interval in busy_intervals
        ]
        return _merge_busy_intervals(normalized), True, None
    except Exception as exc:
        logger.warning(
            "Calendar availability lookup failed for company_id=%s detail=%s",
            company_id,
            exc,
        )
        return [], True, str(exc)


def _candidate_slots_for_day(
    *,
    day_start: datetime,
    day_end: datetime,
    duration_minutes: int,
    busy_intervals: list[tuple[datetime, datetime]],
    horizon_end: datetime | None = None,
) -> list[tuple[datetime, datetime]]:
    slots: list[tuple[datetime, datetime]] = []
    candidate = day_start
    slot_duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=DEFAULT_AVAILABILITY_STEP_MINUTES)
    effective_day_end = min(day_end, horizon_end) if horizon_end is not None else day_end
    latest_start = effective_day_end - slot_duration
    while candidate <= latest_start:
        candidate_end = candidate + slot_duration
        if candidate_end <= effective_day_end and not _slot_overlaps_busy(candidate, candidate_end, busy_intervals):
            slots.append((candidate, candidate_end))
        candidate += step
    return slots


def _select_preferred_slots(
    slots_by_day: list[list[tuple[datetime, datetime]]],
    *,
    max_options: int,
) -> list[tuple[datetime, datetime]]:
    selected: list[tuple[datetime, datetime]] = []
    selected_dates: set[date] = set()
    for day_slots in slots_by_day:
        if not day_slots:
            continue
        first_slot = day_slots[0]
        slot_date = first_slot[0].date()
        if slot_date in selected_dates:
            continue
        selected.append(first_slot)
        selected_dates.add(slot_date)
        if len(selected) >= max_options:
            return selected

    if len(selected) < max_options:
        for day_slots in slots_by_day:
            for slot in day_slots[1:]:
                if len(selected) >= max_options:
                    return selected
                if slot in selected:
                    continue
                selected.append(slot)
    return selected


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


def _appointment_list_stmt(
    db: Session,
    *,
    company_id: UUID,
    scheduled_from: date | None = None,
    scheduled_to: date | None = None,
    status: str | None = None,
    contact_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    source: str | None = None,
) -> Select:
    company = _get_company(db, company_id=company_id)
    tzinfo = _normalize_timezone(company.timezone)
    stmt = select(Appointment).where(Appointment.company_id == company_id)

    if scheduled_from is not None:
        range_start = datetime.combine(scheduled_from, time.min, tzinfo=tzinfo).astimezone(UTC)
        stmt = stmt.where(Appointment.scheduled_at >= range_start)
    if scheduled_to is not None:
        range_end = datetime.combine(scheduled_to + timedelta(days=1), time.min, tzinfo=tzinfo).astimezone(UTC)
        stmt = stmt.where(Appointment.scheduled_at < range_end)
    if status:
        stmt = stmt.where(Appointment.status == status)
    if contact_id is not None:
        stmt = stmt.where(Appointment.contact_id == contact_id)
    if assigned_user_id is not None:
        stmt = stmt.where(Appointment.assigned_user_id == assigned_user_id)
    if source == "inbox":
        stmt = stmt.where(Appointment.conversation_id.is_not(None))
    elif source == "manual":
        stmt = stmt.where(Appointment.conversation_id.is_(None))

    return stmt.order_by(Appointment.scheduled_at.asc(), Appointment.created_at.asc(), Appointment.id.asc())


def list_appointments(
    db: Session,
    *,
    company_id: UUID,
    limit: int,
    offset: int,
    focus_appointment_id: UUID | None = None,
    scheduled_from: date | None = None,
    scheduled_to: date | None = None,
    status: str | None = None,
    contact_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    source: str | None = None,
) -> list[Appointment]:
    stmt = _appointment_list_stmt(
        db,
        company_id=company_id,
        scheduled_from=scheduled_from,
        scheduled_to=scheduled_to,
        status=status,
        contact_id=contact_id,
        assigned_user_id=assigned_user_id,
        source=source,
    )
    appointments = list(db.scalars(stmt.limit(limit).offset(offset)))
    if focus_appointment_id is None or any(appointment.id == focus_appointment_id for appointment in appointments):
        return appointments

    focused_appointment = db.scalar(
        _appointment_list_stmt(
            db,
            company_id=company_id,
            scheduled_from=scheduled_from,
            scheduled_to=scheduled_to,
            status=status,
            contact_id=contact_id,
            assigned_user_id=assigned_user_id,
            source=source,
        ).where(Appointment.id == focus_appointment_id)
    )
    if focused_appointment is None:
        return appointments

    if len(appointments) >= limit:
        appointments = appointments[: max(limit - 1, 0)]
    appointments.append(focused_appointment)
    appointments.sort(key=lambda appointment: (appointment.scheduled_at, appointment.created_at, appointment.id))
    return appointments[:limit]


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


def get_appointment_availability(
    db: Session,
    *,
    company_id: UUID,
    payload: AppointmentAvailabilityRequest,
) -> AppointmentAvailabilityRead:
    if payload.conversation_id is not None:
        get_conversation(db, company_id=company_id, conversation_id=payload.conversation_id)
    section, tzinfo = _get_company_operational_section(db, company_id=company_id)
    duration_minutes = payload.duration_minutes or _get_default_duration_minutes(section)
    now_local = datetime.now(tzinfo)
    start_day = (now_local + timedelta(days=1)).date()
    effective_horizon_days = min(payload.horizon_days, DEFAULT_AVAILABILITY_HORIZON_DAYS)
    end_day = start_day + timedelta(days=effective_horizon_days - 1)
    range_start = datetime.combine(start_day, time.min, tzinfo=tzinfo)
    range_end = datetime.combine(end_day, time.max.replace(microsecond=0), tzinfo=tzinfo)

    internal_busy_intervals = _collect_internal_busy_intervals(
        db,
        company_id=company_id,
        start_at=range_start,
        end_at=range_end,
        tzinfo=tzinfo,
    )
    calendar_busy_intervals, calendar_active, calendar_error = _collect_calendar_busy_intervals(
        db,
        company_id=company_id,
        start_at=range_start,
        end_at=range_end,
        tzinfo=tzinfo,
    )
    combined_busy_intervals = _merge_busy_intervals(internal_busy_intervals + calendar_busy_intervals)

    slots_by_day: list[list[tuple[datetime, datetime]]] = []
    for day_offset in range(effective_horizon_days):
        day = start_day + timedelta(days=day_offset)
        day_window = _day_window_for_date(section, day=day, preferred_period=payload.preferred_period, tzinfo=tzinfo)
        if day_window is None:
            slots_by_day.append([])
            continue
        day_slots = _candidate_slots_for_day(
            day_start=day_window[0],
            day_end=day_window[1],
            duration_minutes=duration_minutes,
            busy_intervals=combined_busy_intervals,
            horizon_end=range_end,
        )
        slots_by_day.append(day_slots)

    selected_slots = _select_preferred_slots(slots_by_day, max_options=3)
    validation_source = "external" if calendar_active and not calendar_error else "internal"
    if calendar_active and calendar_error:
        validation_source = "internal_fallback"

    if payload.conversation_id is not None:
        create_event(
            db,
            company_id=company_id,
            event_type="conversation.appointment_preference_selected",
            payload={
                "conversation_id": str(payload.conversation_id),
                "preferred_period": payload.preferred_period,
                "duration_minutes": duration_minutes,
                "horizon_days": effective_horizon_days,
                "max_options": 3,
                "selected_at": datetime.now(UTC).isoformat(),
            },
        )
        db.commit()

    return AppointmentAvailabilityRead(
        company_id=company_id,
        timezone=getattr(tzinfo, "key", str(tzinfo)),
        preferred_period=payload.preferred_period,
        duration_minutes=duration_minutes,
        horizon_days=effective_horizon_days,
        max_options=3,
        calendar_integration_active=calendar_active,
        validation_source=validation_source,
        validation_error=calendar_error,
        options=[
            AppointmentAvailabilityOption(scheduled_at=start, ends_at=end)
            for start, end in selected_slots
        ],
    )


def _ensure_appointment_slot_available(
    db: Session,
    *,
    company_id: UUID,
    scheduled_at: datetime,
    duration_minutes: int,
    ignore_appointment_id: UUID | None = None,
) -> None:
    db.scalar(select(Company.id).where(Company.id == company_id).with_for_update())
    section, tzinfo = _get_company_operational_section(db, company_id=company_id)
    start_at = _datetime_in_timezone(scheduled_at, tzinfo)
    end_at = start_at + timedelta(minutes=duration_minutes)
    operational_window = _operational_window_for_date(section, day=start_at.date(), tzinfo=tzinfo)
    if operational_window is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment slot is outside operational hours",
        )
    operational_start, operational_end = operational_window
    if start_at < operational_start or end_at > operational_end:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment slot is outside operational hours",
        )
    internal_busy_intervals = _collect_internal_busy_intervals(
        db,
        company_id=company_id,
        start_at=start_at,
        end_at=end_at,
        tzinfo=tzinfo,
        ignore_appointment_id=ignore_appointment_id,
    )
    calendar_busy_intervals, calendar_active, calendar_error = _collect_calendar_busy_intervals(
        db,
        company_id=company_id,
        start_at=start_at,
        end_at=end_at,
        tzinfo=tzinfo,
    )
    busy_intervals = internal_busy_intervals
    if calendar_active and not calendar_error:
        busy_intervals = _merge_busy_intervals(internal_busy_intervals + calendar_busy_intervals)
    if _slot_overlaps_busy(start_at, end_at, busy_intervals):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment slot is no longer available",
        )


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
    section, _ = _get_company_operational_section(db, company_id=company_id)
    duration_minutes = payload.duration_minutes or _get_default_duration_minutes(section)
    _ensure_appointment_slot_available(
        db,
        company_id=company_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=duration_minutes,
    )
    appointment = Appointment(
        company_id=company_id,
        contact_id=payload.contact_id,
        conversation_id=payload.conversation_id,
        assigned_user_id=payload.assigned_user_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=duration_minutes,
        notes=payload.notes,
    )
    db.add(appointment)
    db.flush()
    create_event(
        db,
        company_id=company_id,
        event_type="appointment.created",
        payload={
            "appointment_id": str(appointment.id),
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
            "scheduled_at": appointment.scheduled_at.isoformat(),
        },
    )
    db.commit()
    db.refresh(appointment)
    realtime_manager.publish(
        company_id,
        "appointment.created",
        {
            "appointment_id": str(appointment.id),
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
            "scheduled_at": appointment.scheduled_at.isoformat(),
        },
    )
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
                "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
                "reason": str(exc),
                "sync_status": sync_status,
                "external_calendar_event_id": appointment.external_calendar_event_id,
            },
        )
        db.commit()
        realtime_manager.publish(
            company_id,
            "appointment.calendar_sync_failed",
            {
                "appointment_id": str(appointment.id),
                "conversation_id": str(appointment.conversation_id)
                if appointment.conversation_id
                else None,
                "reason": str(exc),
                "sync_status": sync_status,
                "external_calendar_event_id": appointment.external_calendar_event_id,
            },
        )
        sync_result = None
    if sync_result is not None:
        _mark_calendar_sync_success(appointment, sync_result)
        create_event(
            db,
            company_id=company_id,
            event_type="appointment.calendar_synced",
            payload={
                "appointment_id": str(appointment.id),
                "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
                "provider": sync_result.raw.get("provider"),
                "external_calendar_event_id": sync_result.external_event_id,
                "sync_status": appointment.calendar_sync_status,
            },
        )
        db.commit()
        realtime_manager.publish(
            company_id,
            "appointment.calendar_synced",
            {
                "appointment_id": str(appointment.id),
                "conversation_id": str(appointment.conversation_id)
                if appointment.conversation_id
                else None,
                "provider": sync_result.raw.get("provider"),
                "external_calendar_event_id": sync_result.external_event_id,
                "sync_status": appointment.calendar_sync_status,
            },
        )
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
    if any(key in data and data[key] is None for key in ("scheduled_at", "duration_minutes")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use omission, not null, for appointment updates",
        )
    if {"scheduled_at", "duration_minutes"} & data.keys():
        next_scheduled_at = data.get("scheduled_at", appointment.scheduled_at)
        next_duration_minutes = (
            data.get("duration_minutes") if data.get("duration_minutes") is not None else appointment.duration_minutes
        )
        _ensure_appointment_slot_available(
            db,
            company_id=company_id,
            scheduled_at=next_scheduled_at,
            duration_minutes=next_duration_minutes,
            ignore_appointment_id=appointment.id,
        )
    for field, value in data.items():
        setattr(appointment, field, value)
    db.commit()
    db.refresh(appointment)
    create_event(
        db,
        company_id=company_id,
        event_type="appointment.updated",
        payload={
            "appointment_id": str(appointment.id),
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
            "scheduled_at": appointment.scheduled_at.isoformat(),
            "status": appointment.status,
        },
    )
    db.commit()
    realtime_manager.publish(
        company_id,
        "appointment.updated",
        {
            "appointment_id": str(appointment.id),
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
            "scheduled_at": appointment.scheduled_at.isoformat(),
            "status": appointment.status,
        },
    )
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
                "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
                "reason": str(exc),
                "sync_status": sync_status,
                "external_calendar_event_id": appointment.external_calendar_event_id,
            },
        )
        db.commit()
        realtime_manager.publish(
            company_id,
            "appointment.calendar_sync_failed",
            {
                "appointment_id": str(appointment.id),
                "conversation_id": str(appointment.conversation_id)
                if appointment.conversation_id
                else None,
                "reason": str(exc),
                "sync_status": sync_status,
                "external_calendar_event_id": appointment.external_calendar_event_id,
            },
        )
        sync_result = None
    if sync_result is not None:
        _mark_calendar_sync_success(appointment, sync_result)
        create_event(
            db,
            company_id=company_id,
            event_type="appointment.calendar_synced",
            payload={
                "appointment_id": str(appointment.id),
                "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
                "provider": sync_result.raw.get("provider"),
                "external_calendar_event_id": sync_result.external_event_id,
                "sync_status": appointment.calendar_sync_status,
            },
        )
        db.commit()
        realtime_manager.publish(
            company_id,
            "appointment.calendar_synced",
            {
                "appointment_id": str(appointment.id),
                "conversation_id": str(appointment.conversation_id)
                if appointment.conversation_id
                else None,
                "provider": sync_result.raw.get("provider"),
                "external_calendar_event_id": sync_result.external_event_id,
                "sync_status": appointment.calendar_sync_status,
            },
        )
        db.refresh(appointment)
    return appointment


def _shared_schedule_from_operational_config(operational_config: dict) -> AppointmentOperationalConfigRead:
    draft_section = operational_config.get("draft") if isinstance(operational_config, dict) else {}
    published_section = operational_config.get("published") if isinstance(operational_config, dict) else {}
    draft_schedule = draft_section.get("schedule") if isinstance(draft_section, dict) else {}
    published_schedule = published_section.get("schedule") if isinstance(published_section, dict) else {}
    if not isinstance(published_schedule, dict):
        published_schedule = draft_schedule if isinstance(draft_schedule, dict) else {}
    return AppointmentOperationalConfigRead(
        status=str(operational_config.get("status") or "draft"),
        version=int(operational_config.get("version") or 1),
        published_at=operational_config.get("published_at"),
        draft=draft_schedule if isinstance(draft_schedule, dict) else {},
        published=published_schedule if isinstance(published_schedule, dict) else {},
    )


def get_shared_operational_config(db: Session, *, company_id: UUID) -> AppointmentOperationalConfigRead:
    agent = db.scalar(
        select(AiAgent)
        .where(AiAgent.company_id == company_id)
        .order_by(AiAgent.updated_at.desc(), AiAgent.created_at.desc())
    )
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI agent not found")
    operational_config = build_operational_config(
        agent.rules if isinstance(agent.rules, dict) else {},
        fallback_timezone=_get_company(db, company_id=company_id).timezone,
    )
    return _shared_schedule_from_operational_config(operational_config)


def update_shared_operational_config(
    db: Session,
    *,
    company_id: UUID,
    payload: AppointmentOperationalConfigUpdate,
    actor_user: User | None = None,
) -> AppointmentOperationalConfigRead:
    from app.ai.service import update_operational_config as update_ai_operational_config

    agent = db.scalar(
        select(AiAgent)
        .where(AiAgent.company_id == company_id)
        .order_by(AiAgent.updated_at.desc(), AiAgent.created_at.desc())
    )
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI agent not found")
    operational_config = build_operational_config(
        agent.rules if isinstance(agent.rules, dict) else {},
        fallback_timezone=_get_company(db, company_id=company_id).timezone,
    )
    current_config = _shared_schedule_from_operational_config(operational_config)
    if payload.version != current_config.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agenda config changed; reload and retry",
        )
    draft_section = operational_config.get("draft") if isinstance(operational_config, dict) else {}
    published_section = operational_config.get("published") if isinstance(operational_config, dict) else {}
    next_operational_config = {
        "status": payload.status,
        "version": current_config.version + 1,
        "published_at": payload.published_at,
        "draft": {
            **(draft_section if isinstance(draft_section, dict) else {}),
            "schedule": payload.draft.model_dump(),
        },
        "published": {
            **(published_section if isinstance(published_section, dict) else {}),
            "schedule": payload.published.model_dump(),
        },
    }
    updated_agent = update_ai_operational_config(
        db,
        company_id=company_id,
        agent_id=agent.id,
        payload=next_operational_config,
        actor_user=actor_user,
    )
    updated_operational_config = build_operational_config(
        updated_agent.rules if isinstance(updated_agent.rules, dict) else {},
        fallback_timezone=_get_company(db, company_id=company_id).timezone,
    )
    return _shared_schedule_from_operational_config(updated_operational_config)


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
        payload={
            "appointment_id": str(appointment.id),
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
        },
    )
    db.commit()
    db.refresh(appointment)
    realtime_manager.publish(
        company_id,
        "appointment.cancelled",
        {
            "appointment_id": str(appointment.id),
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
        },
    )
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

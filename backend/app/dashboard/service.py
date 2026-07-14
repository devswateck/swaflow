from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment
from app.conversations.models import Conversation
from app.dashboard.schemas import DashboardAnalyticsRead, DashboardAnalyticsPointRead, DashboardSummaryRead
from app.messages.models import Message
from app.orders.models import Order, OrderItem

logger = logging.getLogger(__name__)


def _tenant_timezone(db: Session, *, company_id: UUID) -> ZoneInfo:
    from app.companies.models import Company

    company = db.scalar(select(Company).where(Company.id == company_id))
    timezone_name = company.timezone if company is not None else None
    if timezone_name is None:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(timezone_name)
    except Exception:
        logger.warning(
            "Invalid company timezone found in dashboard analytics; falling back to UTC",
            extra={"company_id": str(company_id), "timezone": timezone_name},
        )
        return ZoneInfo("UTC")


def _today_in_timezone(timezone: ZoneInfo) -> date:
    return datetime.now(timezone).date()


def _resolve_date_window(
    *,
    timezone: ZoneInfo,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date]:
    resolved_to = date_to or _today_in_timezone(timezone)
    resolved_from = date_from or (resolved_to - timedelta(days=29))
    if resolved_from > resolved_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid analytics date range",
        )
    return resolved_from, resolved_to


def _day_start(value: date, *, timezone: ZoneInfo) -> datetime:
    return datetime.combine(value, datetime.min.time(), tzinfo=timezone).astimezone(UTC)


def _day_end(value: date, *, timezone: ZoneInfo) -> datetime:
    return datetime.combine(value + timedelta(days=1), datetime.min.time(), tzinfo=timezone).astimezone(UTC)


def _bucket_day(value: datetime | None, *, timezone: ZoneInfo) -> date | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(timezone).date()


def _date_series(start_date: date, end_date: date) -> list[date]:
    current = start_date
    series: list[date] = []
    while current <= end_date:
        series.append(current)
        current += timedelta(days=1)
    return series


def _conversation_scope_stmt(
    *,
    company_id: UUID,
    start_at: datetime,
    end_at: datetime,
    assigned_user_id: UUID | None,
    status_filter: str | None,
    funnel_id: UUID | None,
    funnel_step_id: UUID | None,
    product_id: UUID | None,
) -> object:
    stmt = select(Conversation.id).where(Conversation.company_id == company_id)
    if assigned_user_id is not None:
        stmt = stmt.where(Conversation.assigned_user_id == assigned_user_id)
    if status_filter:
        stmt = stmt.where(Conversation.status == status_filter)
    if funnel_id is not None:
        stmt = stmt.where(Conversation.funnel_id == funnel_id)
    if funnel_step_id is not None:
        stmt = stmt.where(Conversation.funnel_step_id == funnel_step_id)
    if product_id is not None:
        stmt = stmt.where(
            exists(
                select(1)
                .select_from(OrderItem)
                .join(Order, Order.id == OrderItem.order_id)
                .where(
                    OrderItem.company_id == company_id,
                    OrderItem.product_id == product_id,
                    Order.company_id == company_id,
                    Order.conversation_id == Conversation.id,
                    Order.created_at >= start_at,
                    Order.created_at < end_at,
                )
            )
        )
    return stmt


def get_dashboard_summary(db: Session, *, company_id: UUID) -> DashboardSummaryRead:
    total_conversations = db.scalar(
        select(func.count(Conversation.id)).where(Conversation.company_id == company_id)
    )
    total_unread = db.scalar(
        select(func.coalesce(func.sum(Conversation.unread_count), 0)).where(
            Conversation.company_id == company_id
        )
    )
    confirmed_sales_total = db.scalar(
        select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.company_id == company_id,
            Order.status == "paid",
        )
    )
    appointments_total = db.scalar(
        select(func.count(Appointment.id)).where(Appointment.company_id == company_id)
    )
    return DashboardSummaryRead(
        total_conversations=int(total_conversations or 0),
        total_unread=int(total_unread or 0),
        confirmed_sales_total=confirmed_sales_total or Decimal("0"),
        appointments_total=int(appointments_total or 0),
    )


def get_dashboard_analytics(
    db: Session,
    *,
    company_id: UUID,
    date_from: date | None,
    date_to: date | None,
    assigned_user_id: UUID | None = None,
    conversation_status: str | None = None,
    funnel_id: UUID | None = None,
    funnel_step_id: UUID | None = None,
    product_id: UUID | None = None,
) -> DashboardAnalyticsRead:
    timezone = _tenant_timezone(db, company_id=company_id)
    resolved_from, resolved_to = _resolve_date_window(
        timezone=timezone,
        date_from=date_from,
        date_to=date_to,
    )
    start_at = _day_start(resolved_from, timezone=timezone)
    end_at = _day_end(resolved_to, timezone=timezone)
    has_conversation_filters = any(
        [
            assigned_user_id is not None,
            bool(conversation_status),
            funnel_id is not None,
            funnel_step_id is not None,
            product_id is not None,
        ]
    )
    conversation_scope_stmt = (
        _conversation_scope_stmt(
            company_id=company_id,
            start_at=start_at,
            end_at=end_at,
            assigned_user_id=assigned_user_id,
            status_filter=conversation_status,
            funnel_id=funnel_id,
            funnel_step_id=funnel_step_id,
            product_id=product_id,
        )
        if has_conversation_filters
        else None
    )

    conversations_stmt = select(
        func.count(Conversation.id),
        func.coalesce(func.sum(Conversation.unread_count), 0),
    ).where(
        Conversation.company_id == company_id,
        or_(
            Conversation.created_at >= start_at,
            Conversation.last_message_at >= start_at,
        ),
        or_(
            Conversation.created_at < end_at,
            Conversation.last_message_at < end_at,
        ),
    )
    if conversation_scope_stmt is not None:
        conversations_stmt = conversations_stmt.where(Conversation.id.in_(conversation_scope_stmt))
    total_conversations, total_unread = db.execute(conversations_stmt).one()

    buckets = _date_series(resolved_from, resolved_to)
    day_windows = [
        (day, _day_start(day, timezone=timezone), _day_end(day, timezone=timezone))
        for day in buckets
    ]

    message_columns = []
    for index, (_, day_start, day_end) in enumerate(day_windows):
        received_condition = and_(
            Message.created_at >= day_start,
            Message.created_at < day_end,
            Message.sender_type == "customer",
        )
        sent_condition = and_(
            Message.created_at >= day_start,
            Message.created_at < day_end,
            Message.sender_type != "customer",
        )
        message_columns.extend(
            [
                func.coalesce(func.sum(case((received_condition, 1), else_=0)), 0).label(
                    f"messages_received_{index}"
                ),
                func.coalesce(func.sum(case((sent_condition, 1), else_=0)), 0).label(
                    f"messages_sent_{index}"
                ),
            ]
        )
    messages_stmt = select(*message_columns).where(
        Message.company_id == company_id,
        Message.created_at >= start_at,
        Message.created_at < end_at,
    )
    if conversation_scope_stmt is not None:
        messages_stmt = messages_stmt.where(Message.conversation_id.in_(conversation_scope_stmt))
    messages_row = db.execute(messages_stmt).one()

    order_columns = []
    for index, (_, day_start, day_end) in enumerate(day_windows):
        order_window = and_(Order.created_at >= day_start, Order.created_at < day_end)
        order_columns.extend(
            [
                func.coalesce(func.sum(case((order_window, 1), else_=0)), 0).label(f"orders_created_{index}"),
                func.coalesce(
                    func.sum(case((and_(order_window, Order.status == "paid"), 1), else_=0)),
                    0,
                ).label(f"orders_paid_{index}"),
                func.coalesce(
                    func.sum(case((and_(order_window, Order.status == "paid"), Order.total), else_=0)),
                    0,
                ).label(f"orders_paid_total_{index}"),
            ]
        )
    orders_stmt = select(*order_columns).where(
        Order.company_id == company_id,
        Order.created_at >= start_at,
        Order.created_at < end_at,
    )
    if conversation_scope_stmt is not None:
        orders_stmt = orders_stmt.where(Order.conversation_id.in_(conversation_scope_stmt))
    if product_id is not None:
        orders_stmt = orders_stmt.where(
            exists(
                select(1).select_from(OrderItem).where(
                    OrderItem.company_id == company_id,
                    OrderItem.order_id == Order.id,
                    OrderItem.product_id == product_id,
                )
            )
        )
    orders_row = db.execute(orders_stmt).one()

    appointment_columns = []
    for index, (_, day_start, day_end) in enumerate(day_windows):
        appointment_window = and_(Appointment.scheduled_at >= day_start, Appointment.scheduled_at < day_end)
        appointment_columns.extend(
            [
                func.coalesce(func.sum(case((appointment_window, 1), else_=0)), 0).label(
                    f"appointments_total_{index}"
                ),
                func.coalesce(
                    func.sum(case((and_(appointment_window, Appointment.status == "scheduled"), 1), else_=0)),
                    0,
                ).label(f"appointments_scheduled_{index}"),
                func.coalesce(
                    func.sum(case((and_(appointment_window, Appointment.status == "completed"), 1), else_=0)),
                    0,
                ).label(f"appointments_completed_{index}"),
                func.coalesce(
                    func.sum(case((and_(appointment_window, Appointment.status == "cancelled"), 1), else_=0)),
                    0,
                ).label(f"appointments_cancelled_{index}"),
            ]
        )
    appointments_stmt = select(*appointment_columns).where(
        Appointment.company_id == company_id,
        Appointment.scheduled_at >= start_at,
        Appointment.scheduled_at < end_at,
    )
    if assigned_user_id is not None:
        appointments_stmt = appointments_stmt.where(Appointment.assigned_user_id == assigned_user_id)
    if conversation_scope_stmt is not None and (
        conversation_status or funnel_id is not None or funnel_step_id is not None or product_id is not None
    ):
        appointments_stmt = appointments_stmt.where(Appointment.conversation_id.in_(conversation_scope_stmt))
    appointments_row = db.execute(appointments_stmt).one()

    messages_received_by_day: dict[date, int] = {}
    messages_sent_by_day: dict[date, int] = {}
    orders_created_by_day: dict[date, int] = {}
    orders_paid_count_by_day: dict[date, int] = {}
    orders_paid_total_by_day: dict[date, Decimal] = {}
    appointments_total_by_day: dict[date, int] = {}
    appointments_scheduled_by_day: dict[date, int] = {}
    appointments_completed_by_day: dict[date, int] = {}
    appointments_cancelled_by_day: dict[date, int] = {}

    for index, (day, _, _) in enumerate(day_windows):
        messages_received_by_day[day] = int(messages_row._mapping[f"messages_received_{index}"] or 0)
        messages_sent_by_day[day] = int(messages_row._mapping[f"messages_sent_{index}"] or 0)
        orders_created_by_day[day] = int(orders_row._mapping[f"orders_created_{index}"] or 0)
        orders_paid_count_by_day[day] = int(orders_row._mapping[f"orders_paid_{index}"] or 0)
        orders_paid_total_by_day[day] = Decimal(str(orders_row._mapping[f"orders_paid_total_{index}"] or 0))
        appointments_total_by_day[day] = int(appointments_row._mapping[f"appointments_total_{index}"] or 0)
        appointments_scheduled_by_day[day] = int(appointments_row._mapping[f"appointments_scheduled_{index}"] or 0)
        appointments_completed_by_day[day] = int(appointments_row._mapping[f"appointments_completed_{index}"] or 0)
        appointments_cancelled_by_day[day] = int(appointments_row._mapping[f"appointments_cancelled_{index}"] or 0)

    paid_total = sum(orders_paid_total_by_day.values(), start=Decimal("0"))
    appointment_total = sum(appointments_total_by_day.values())
    summary = DashboardSummaryRead(
        total_conversations=int(total_conversations or 0),
        total_unread=int(total_unread or 0),
        confirmed_sales_total=paid_total,
        appointments_total=appointment_total,
    )

    series = [
        DashboardAnalyticsPointRead(
            date=day,
            chats_received=messages_received_by_day[day],
            chats_sent=messages_sent_by_day[day],
            orders_created=orders_created_by_day[day],
            orders_paid=orders_paid_count_by_day[day],
            orders_paid_total=orders_paid_total_by_day[day] or Decimal("0"),
            appointments_scheduled=appointments_scheduled_by_day[day],
            appointments_completed=appointments_completed_by_day[day],
            appointments_cancelled=appointments_cancelled_by_day[day],
        )
        for day in buckets
    ]

    return DashboardAnalyticsRead(
        date_from=resolved_from,
        date_to=resolved_to,
        timezone=timezone.key,
        summary=summary,
        series=series,
    )

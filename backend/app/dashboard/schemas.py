from decimal import Decimal
from datetime import date

from pydantic import BaseModel


class DashboardSummaryRead(BaseModel):
    total_conversations: int
    total_unread: int
    confirmed_sales_total: Decimal
    appointments_total: int


class DashboardAnalyticsPointRead(BaseModel):
    date: date
    chats_received: int
    chats_sent: int
    orders_created: int
    orders_paid: int
    orders_paid_total: Decimal
    appointments_scheduled: int
    appointments_completed: int
    appointments_cancelled: int


class DashboardAnalyticsRead(BaseModel):
    date_from: date
    date_to: date
    timezone: str
    summary: DashboardSummaryRead
    series: list[DashboardAnalyticsPointRead]

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dashboard.schemas import DashboardAnalyticsRead, DashboardSummaryRead
from app.dashboard.service import get_dashboard_analytics, get_dashboard_summary
from app.auth.service import require_module_access
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryRead)
def read_dashboard_summary(
    current_user: User = Depends(require_module_access("dashboard")),
    db: Session = Depends(get_db),
) -> DashboardSummaryRead:
    return get_dashboard_summary(db, company_id=current_user.company_id)


@router.get("/analytics", response_model=DashboardAnalyticsRead)
def read_dashboard_analytics(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    assigned_user_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    funnel_id: UUID | None = Query(default=None),
    funnel_step_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    current_user: User = Depends(require_module_access("dashboard")),
    db: Session = Depends(get_db),
) -> DashboardAnalyticsRead:
    return get_dashboard_analytics(
        db,
        company_id=current_user.company_id,
        date_from=date_from,
        date_to=date_to,
        assigned_user_id=assigned_user_id,
        conversation_status=status,
        funnel_id=funnel_id,
        funnel_step_id=funnel_step_id,
        product_id=product_id,
    )

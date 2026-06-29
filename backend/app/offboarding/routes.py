from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.service import require_roles
from app.core.database import get_db
from app.offboarding import service
from app.users.models import User

router = APIRouter(prefix="/offboarding", tags=["offboarding"])


@router.get("/export/{company_id}")
def export_tenant_package(
    company_id: UUID,
    current_user: User = Depends(require_roles("superadmin")),
    db: Session = Depends(get_db),
) -> Response:
    package = service.build_tenant_export(db, company_id=company_id, actor_user=current_user)
    headers = {
        "Content-Disposition": f'attachment; filename="{package.filename}"',
    }
    return Response(content=package.content, media_type="application/zip", headers=headers)

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.service import get_current_user, is_superadmin, require_roles
from app.companies import service
from app.companies.schemas import CompanyBootstrapRead, CompanyCreate, CompanyRead, CompanyUpdate
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyBootstrapRead, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> dict:
    company, owner = service.create_company_with_owner(db, payload)
    return {"company": company, "owner": owner}


@router.get("", response_model=list[CompanyRead])
def list_companies(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles("superadmin")),
    db: Session = Depends(get_db),
) -> list[object]:
    return service.list_companies(db, limit=limit, offset=offset)


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> object:
    return service.get_company_for_user(
        db,
        company_id=company_id,
        current_company_id=current_user.company_id,
        is_superuser=is_superadmin(current_user),
    )


@router.put("/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
) -> object:
    return service.update_company(
        db,
        company_id=company_id,
        current_company_id=current_user.company_id,
        payload=payload,
        is_superuser=is_superadmin(current_user),
    )

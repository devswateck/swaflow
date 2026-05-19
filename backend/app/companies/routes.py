from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import get_current_user, require_roles
from app.companies import service
from app.companies.schemas import CompanyBootstrapRead, CompanyCreate, CompanyRead, CompanyUpdate
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyBootstrapRead, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> dict:
    company, owner = service.create_company_with_owner(db, payload)
    return {"company": company, "owner": owner}


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
    )


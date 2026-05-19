from uuid import UUID

from fastapi import HTTPException, status


def ensure_same_company(resource_company_id: UUID, current_company_id: UUID) -> None:
    if resource_company_id != current_company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )


from fastapi import APIRouter, Depends

from app.api.auth import get_current_doctor
from app.persistence.database import get_session_factory
from app.persistence.repositories import DepartmentRepository
from app.schemas.department import DepartmentResponse

router = APIRouter(
    prefix="/departments", tags=["departments"], dependencies=[Depends(get_current_doctor)]
)


@router.get("", response_model=list[DepartmentResponse])
async def list_departments() -> list[DepartmentResponse]:
    """返回医生端可选择的启用科室字典。"""
    async with get_session_factory()() as session:
        rows = await DepartmentRepository(session).list_enabled()
        return [
            DepartmentResponse(
                code=row.code,
                name=row.name,
                enabled=row.enabled,
                sort_order=row.sort_order,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

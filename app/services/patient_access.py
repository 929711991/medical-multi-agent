from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.repositories import PatientRepository


class PatientAccessService:
    """集中执行 V1 的患者访问边界，避免接口直接信任任意 patient_id。"""

    def __init__(self, session: AsyncSession):
        self.repository = PatientRepository(session)

    async def can_access_patient(self, patient_id: str) -> bool:
        return await self.repository.data_scope(patient_id) == "sandbox"


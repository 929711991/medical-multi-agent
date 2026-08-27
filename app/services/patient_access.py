from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.repositories import PatientRepository


class PatientAccessService:
    """集中执行 V1 的患者访问边界，避免接口直接信任任意 patient_id。"""

    def __init__(self, session: AsyncSession):
        self.repository = PatientRepository(session)

    async def can_access_demo_patient(self, patient_id: str) -> bool:
        # V1 没有完整身份系统，只允许显式标记的虚构 DEMO 编号。
        if not patient_id.startswith("DEMO-"):
            return False
        return await self.repository.exists(patient_id)


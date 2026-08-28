from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.repositories import PatientRepository


class PatientAccessService:
    """集中执行 V1 的患者访问边界，避免接口直接信任任意 patient_id。"""

    def __init__(self, session: AsyncSession):
        """使用当前会话初始化患者访问边界服务。"""
        self.repository = PatientRepository(session)

    async def can_access_patient(self, patient_id: str) -> bool:
        """判断患者是否属于当前允许访问的沙箱数据范围。"""
        return await self.repository.data_scope(patient_id) == "sandbox"

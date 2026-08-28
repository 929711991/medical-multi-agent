from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.identifiers import identifier_to_bigint
from app.persistence.models import MedicalCase, MedicalVisit
from app.persistence.repositories import PatientRepository


class PatientAccessService:
    """集中执行 V1 的患者访问边界，避免接口直接信任任意 patient_id。"""

    def __init__(self, session: AsyncSession):
        """使用当前会话初始化患者访问边界服务。"""
        self.repository = PatientRepository(session)

    async def can_access_patient(self, patient_id: str, doctor_department: str | None = None) -> bool:
        """允许沙箱患者；Consumer 患者必须有转诊病例且接诊科室匹配当前医生。"""
        if await self.repository.data_scope(patient_id) == "sandbox":
            return True
        if not doctor_department:
            return False
        database_patient_id = identifier_to_bigint(patient_id, namespace="patient")
        if database_patient_id is None:
            return False
        allowed = await self.repository.session.scalar(
            select(MedicalCase.id)
            .join(MedicalVisit, MedicalVisit.id == MedicalCase.visit_id)
            .where(
                MedicalCase.patient_id == database_patient_id,
                MedicalCase.source_channel == "wechat_mini_program",
                MedicalVisit.department == doctor_department,
            )
            .limit(1)
        )
        return allowed is not None

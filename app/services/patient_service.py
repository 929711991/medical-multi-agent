from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import MedicalVisit, Patient
from app.persistence.repositories import DepartmentRepository, PatientRepository


class PatientService:
    """编排患者与接诊事务，保证不会产生只有患者没有首次接诊的半状态。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.patients = PatientRepository(session)
        self.departments = DepartmentRepository(session)

    async def create_patient_with_visit(
        self,
        *,
        name: str,
        birth_date: date | None,
        sex: str,
        history: list[str],
        department_code: str,
        chief_complaint: str,
        data_scope: str = "sandbox",
        source_channel: str = "doctor_web",
    ) -> tuple[Patient, MedicalVisit]:
        department = await self.departments.get_enabled(department_code)
        if department is None:
            raise LookupError("DEPARTMENT_NOT_FOUND")
        try:
            patient = await self.patients.create(
                name=name,
                birth_date=birth_date,
                sex=sex,
                history=history,
                data_scope=data_scope,
                source_channel=source_channel,
                commit=False,
            )
            visit = await self.patients.create_visit(
                patient_id=patient.id,
                department_code=department.code,
                department=department.name,
                chief_complaint=chief_complaint,
                record={"source_channel": source_channel},
                commit=False,
            )
            await self.session.commit()
            await self.session.refresh(patient)
            await self.session.refresh(visit)
            return patient, visit
        except Exception:
            await self.session.rollback()
            raise

    async def create_visit(
        self,
        *,
        patient_id: str,
        department_code: str,
        chief_complaint: str,
        record: dict[str, Any] | None = None,
    ) -> MedicalVisit:
        if not await self.patients.exists(patient_id):
            raise LookupError("PATIENT_NOT_FOUND")
        department = await self.departments.get_enabled(department_code)
        if department is None:
            raise LookupError("DEPARTMENT_NOT_FOUND")
        return await self.patients.create_visit(
            patient_id=patient_id,
            department_code=department.code,
            department=department.name,
            chief_complaint=chief_complaint,
            record=record,
        )

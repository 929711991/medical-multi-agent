from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.persistence.models import (
    Allergy,
    Doctor,
    ImagingReport,
    LabResult,
    MedicalAssessment,
    MedicalCase,
    MedicalVisit,
    Medication,
    Patient,
)


class PatientRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exists(self, patient_id: str) -> bool:
        return await self.session.get(Patient, patient_id) is not None

    async def summary(self, patient_id: str) -> dict[str, Any]:
        patient = await self.session.get(Patient, patient_id)
        if patient is None:
            return {"found": False, "patient_id": patient_id, "message": "未找到患者"}
        return {
            "found": True,
            "patient_id": patient.id,
            "demo_label": patient.demo_label,
            "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
            "sex": patient.sex,
            "summary": patient.summary_json,
        }

    async def visits(self, patient_id: str) -> dict[str, Any]:
        return await self._records(
            patient_id,
            MedicalVisit,
            MedicalVisit.visit_time,
            lambda x: {
                "id": x.id,
                "visit_time": x.visit_time.isoformat(),
                "department": x.department,
                "chief_complaint": x.chief_complaint,
                "record": x.record_json,
            },
        )

    async def labs(self, patient_id: str) -> dict[str, Any]:
        return await self._records(
            patient_id,
            LabResult,
            LabResult.observed_at,
            lambda x: {
                "id": x.id,
                "observed_at": x.observed_at.isoformat(),
                "test_name": x.test_name,
                "value": x.value,
                "reference_range": x.reference_range,
                "abnormal_flag": x.abnormal_flag,
            },
        )

    async def imaging(self, patient_id: str) -> dict[str, Any]:
        return await self._records(
            patient_id,
            ImagingReport,
            ImagingReport.observed_at,
            lambda x: {
                "id": x.id,
                "observed_at": x.observed_at.isoformat(),
                "modality": x.modality,
                "body_part": x.body_part,
                "findings": x.findings,
                "impression": x.impression,
            },
        )

    async def medications(self, patient_id: str) -> dict[str, Any]:
        return await self._records(
            patient_id,
            Medication,
            Medication.started_at,
            lambda x: {
                "id": x.id,
                "name": x.name,
                "dose": x.dose,
                "route": x.route,
                "started_at": x.started_at.isoformat() if x.started_at else None,
                "ended_at": x.ended_at.isoformat() if x.ended_at else None,
            },
        )

    async def allergies(self, patient_id: str) -> dict[str, Any]:
        return await self._records(
            patient_id,
            Allergy,
            Allergy.observed_at,
            lambda x: {
                "id": x.id,
                "substance": x.substance,
                "reaction": x.reaction,
                "severity": x.severity,
                "observed_at": x.observed_at.isoformat() if x.observed_at else None,
            },
        )

    async def all_records(self, patient_id: str) -> dict[str, Any]:
        if not await self.exists(patient_id):
            return {"found": False, "patient_id": patient_id, "message": "未找到患者", "records": {}}
        return {
            "found": True,
            "patient_id": patient_id,
            "records": {
                "summary": await self.summary(patient_id),
                "visits": (await self.visits(patient_id))["items"],
                "labs": (await self.labs(patient_id))["items"],
                "imaging": (await self.imaging(patient_id))["items"],
                "medications": (await self.medications(patient_id))["items"],
                "allergies": (await self.allergies(patient_id))["items"],
            },
        }

    async def _records(self, patient_id: str, model: Any, order: Any, serializer: Any) -> dict[str, Any]:
        if not await self.exists(patient_id):
            return {"found": False, "patient_id": patient_id, "message": "未找到患者", "items": []}
        rows = (await self.session.scalars(select(model).where(model.patient_id == patient_id).order_by(order.desc()))).all()
        return {"found": True, "patient_id": patient_id, "items": [serializer(row) for row in rows]}


class DoctorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def info(self, doctor_id: str) -> dict[str, Any]:
        doctor = await self.session.get(Doctor, doctor_id)
        if doctor is None:
            return {"found": False, "doctor_id": doctor_id, "message": "未找到医生"}
        return {
            "found": True,
            "doctor_id": doctor.id,
            "demo_name": doctor.demo_name,
            "department": doctor.department,
            "title": doctor.title,
        }


class CaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, case_id: str, patient_id: str, thread_id: str, question: str) -> MedicalCase:
        case = MedicalCase(id=case_id, patient_id=patient_id, thread_id=thread_id, question=question)
        case.assessments.append(MedicalAssessment(review_status="PENDING"))
        self.session.add(case)
        await self.session.commit()
        await self.session.refresh(case)
        return case

    async def get(self, case_id: str) -> MedicalCase | None:
        statement = select(MedicalCase).where(MedicalCase.id == case_id).options(selectinload(MedicalCase.assessments))
        return (await self.session.scalars(statement)).first()

    async def set_draft(self, case_id: str, result: dict[str, Any], risk_level: str) -> None:
        case = await self.get(case_id)
        if case is None:
            raise LookupError("未找到病例")
        case.status = "PENDING_REVIEW"
        case.risk_level = risk_level
        case.assessments[0].ai_result_json = result
        await self.session.commit()

    async def set_status(self, case_id: str, status: str) -> None:
        case = await self.get(case_id)
        if case is None:
            raise LookupError("未找到病例")
        case.status = status
        await self.session.commit()

    async def save_review(
        self,
        case_id: str,
        *,
        action: str,
        reviewer_id: str,
        result: dict[str, Any] | None,
        reason: str | None,
    ) -> None:
        case = await self.get(case_id)
        if case is None:
            raise LookupError("未找到病例")
        assessment = case.assessments[0]
        assessment.review_status = action.upper()
        assessment.reviewer_id = reviewer_id
        assessment.doctor_result_json = result
        assessment.review_reason = reason
        assessment.reviewed_at = datetime.now(UTC)
        case.status = "REJECTED" if action == "reject" else "FINAL"
        await self.session.commit()

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.consumer_repositories import ConsumerPatientRelationRepository
from app.persistence.models import Patient
from app.persistence.repositories import PatientRepository


class ConsumerPatientService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.patients = PatientRepository(session)
        self.relations = ConsumerPatientRelationRepository(session)

    async def create_profile(
        self,
        *,
        user_id: str,
        name: str,
        sex: str,
        birth_date: date | None,
        relation_type: str,
        self_reported_history: list[str],
    ) -> Patient:
        try:
            patient = await self.patients.create(
                name=name,
                sex=sex,
                birth_date=birth_date,
                history=self_reported_history,
                data_scope="consumer",
                source_channel="wechat_mini_program",
                commit=False,
            )
            patient.summary_json = {
                "self_reported_history": [item.strip() for item in self_reported_history if item.strip()],
                "clinician_confirmed_history": [],
            }
            await self.relations.create(
                user_id=user_id,
                patient_id=patient.id,
                relation_type=relation_type,
                permission="MANAGE",
                commit=False,
            )
            await self.session.commit()
            await self.session.refresh(patient)
            return patient
        except Exception:
            await self.session.rollback()
            raise

    async def update_profile(
        self,
        patient_id: str,
        *,
        name: str | None = None,
        birth_date: date | None = None,
        sex: str | None = None,
        self_reported_history: list[str] | None = None,
    ) -> Patient | None:
        patient = await self.patients._get(patient_id)
        if patient is None:
            return None
        if name is not None:
            patient.display_name = name.strip()
        if birth_date is not None:
            patient.birth_date = birth_date
        if sex is not None:
            patient.sex = sex
        if self_reported_history is not None:
            summary = dict(patient.summary_json or {})
            summary["self_reported_history"] = [
                item.strip() for item in self_reported_history if item.strip()
            ]
            patient.summary_json = summary
        await self.session.commit()
        await self.session.refresh(patient)
        return patient

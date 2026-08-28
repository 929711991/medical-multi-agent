from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.consumer_repositories import (
    ConsultationRepository,
    ConsumerPatientRelationRepository,
)


PERMISSION_RANK = {"VIEW": 1, "CONTRIBUTE": 2, "MANAGE": 3}


class ConsumerPatientAccessService:
    def __init__(self, session: AsyncSession):
        self.relations = ConsumerPatientRelationRepository(session)

    async def can_access_patient(
        self, user_id: str, patient_id: str, required_permission: str = "VIEW"
    ) -> bool:
        relation = await self.relations.get(user_id, patient_id)
        return bool(
            relation
            and PERMISSION_RANK.get(relation.permission, 0)
            >= PERMISSION_RANK.get(required_permission, 99)
        )


class ConsumerConsultationAccessService:
    def __init__(self, session: AsyncSession):
        self.consultations = ConsultationRepository(session)

    async def can_access_consultation(self, user_id: str, consultation_id: str) -> bool:
        return await self.consultations.can_access(consultation_id, user_id)

    async def can_contribute(self, user_id: str, consultation_id: str) -> bool:
        permission = await self.consultations.access_permission(consultation_id, user_id)
        return permission in {"CONTRIBUTE", "MANAGE"}

from fastapi import APIRouter, Depends, HTTPException

from app.api.consumer.dependencies import get_current_consumer
from app.persistence.consumer_repositories import ConsumerPatientRelationRepository
from app.persistence.database import get_session_factory
from app.persistence.models import ConsumerUser
from app.schemas.consumer import ConsumerPatientCreateRequest, ConsumerPatientUpdateRequest
from app.services.consumer_access import ConsumerPatientAccessService
from app.services.consumer_patient import ConsumerPatientService

router = APIRouter(prefix="/patients", tags=["consumer-patients"])


def _patient(patient, relation) -> dict:
    return {
        "patient_id": str(patient.id),
        "name": patient.display_name,
        "sex": patient.sex,
        "birth_date": patient.birth_date,
        "relation_type": relation.relation_type,
        "permission": relation.permission,
        "self_reported_history": (patient.summary_json or {}).get("self_reported_history", []),
        "clinician_confirmed_history": (patient.summary_json or {}).get(
            "clinician_confirmed_history", []
        ),
    }


@router.get("")
async def list_patients(user: ConsumerUser = Depends(get_current_consumer)) -> list[dict]:
    async with get_session_factory()() as session:
        rows = await ConsumerPatientRelationRepository(session).list_patients(user.id)
        return [_patient(patient, relation) for relation, patient in rows]


@router.post("", status_code=201)
async def create_patient(
    payload: ConsumerPatientCreateRequest,
    user: ConsumerUser = Depends(get_current_consumer),
) -> dict:
    async with get_session_factory()() as session:
        patient = await ConsumerPatientService(session).create_profile(
            user_id=str(user.id), **payload.model_dump()
        )
        relation = await ConsumerPatientRelationRepository(session).get(user.id, patient.id)
        assert relation is not None
        return _patient(patient, relation)


@router.patch("/{patient_id}")
async def update_patient(
    patient_id: str,
    payload: ConsumerPatientUpdateRequest,
    user: ConsumerUser = Depends(get_current_consumer),
) -> dict:
    async with get_session_factory()() as session:
        if not await ConsumerPatientAccessService(session).can_access_patient(
            str(user.id), patient_id, "MANAGE"
        ):
            raise HTTPException(status_code=403, detail="无权修改该健康档案")
        patient = await ConsumerPatientService(session).update_profile(
            patient_id, **payload.model_dump(exclude_unset=True)
        )
        if patient is None:
            raise HTTPException(status_code=404, detail="未找到健康档案")
        relation = await ConsumerPatientRelationRepository(session).get(user.id, patient.id)
        assert relation is not None
        return _patient(patient, relation)

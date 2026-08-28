from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import get_current_doctor
from app.persistence.database import get_session_factory
from app.persistence.repositories import PatientRepository
from app.schemas.patient import PatientCreateRequest, PatientCreateResponse, PatientUpdateRequest
from app.services.patient_access import PatientAccessService

router = APIRouter(prefix="/patients", tags=["patients"], dependencies=[Depends(get_current_doctor)])


@router.post("", response_model=PatientCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(payload: PatientCreateRequest) -> PatientCreateResponse:
    async with get_session_factory()() as session:
        patient = await PatientRepository(session).create(
            name=payload.name,
            birth_date=payload.birth_date,
            sex=payload.sex,
            history=payload.history,
            data_scope="sandbox",
            source_channel="doctor_web",
        )
    return PatientCreateResponse(
        patient_id=patient.id,
        name=patient.display_name,
        birth_date=patient.birth_date,
        sex=patient.sex or payload.sex,
        history=patient.summary_json.get("history", []),
        data_scope=patient.data_scope,
        source_channel=patient.source_channel,
    )


@router.get("")
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=120),
    sex: str | None = Query(None, max_length=20),
) -> dict:
    async with get_session_factory()() as session:
        return await PatientRepository(session).list(page=page, page_size=page_size, search=search, sex=sex)


async def _ensure_patient(session, patient_id: str) -> PatientRepository:
    if not await PatientAccessService(session).can_access_patient(patient_id):
        raise HTTPException(status_code=404, detail="未找到患者")
    return PatientRepository(session)


@router.get("/{patient_id}")
async def get_patient(patient_id: str) -> dict:
    async with get_session_factory()() as session:
        repository = await _ensure_patient(session, patient_id)
        return await repository.summary(patient_id)


@router.patch("/{patient_id}")
async def update_patient(patient_id: str, payload: PatientUpdateRequest) -> dict:
    async with get_session_factory()() as session:
        repository = await _ensure_patient(session, patient_id)
        patient = await repository.update_patient(patient_id, **payload.model_dump(exclude_unset=True))
        if patient is None:
            raise HTTPException(status_code=404, detail="未找到患者")
        return await repository.summary(patient_id)


@router.get("/{patient_id}/overview")
async def get_patient_overview(patient_id: str) -> dict:
    async with get_session_factory()() as session:
        repository = await _ensure_patient(session, patient_id)
        summary = await repository.summary(patient_id)
        visits = await repository.visits(patient_id)
        labs = await repository.labs(patient_id)
        imaging = await repository.imaging(patient_id)
        medications = await repository.medications(patient_id)
        allergies = await repository.allergies(patient_id)
        return {
            "patient_id": patient_id,
            "summary": summary,
            "recent_visits": visits["items"][:5],
            "recent_labs": labs["items"][:8],
            "recent_imaging": imaging["items"][:5],
            "current_medications": [item for item in medications["items"] if item["ended_at"] is None],
            "allergies": allergies["items"],
        }


@router.get("/{patient_id}/visits")
async def get_visits(patient_id: str) -> dict:
    async with get_session_factory()() as session:
        return await (await _ensure_patient(session, patient_id)).visits(patient_id)


@router.get("/{patient_id}/labs")
async def get_labs(patient_id: str) -> dict:
    async with get_session_factory()() as session:
        return await (await _ensure_patient(session, patient_id)).labs(patient_id)


@router.get("/{patient_id}/imaging")
async def get_imaging(patient_id: str) -> dict:
    async with get_session_factory()() as session:
        return await (await _ensure_patient(session, patient_id)).imaging(patient_id)


@router.get("/{patient_id}/medications")
async def get_medications(patient_id: str) -> dict:
    async with get_session_factory()() as session:
        return await (await _ensure_patient(session, patient_id)).medications(patient_id)


@router.get("/{patient_id}/allergies")
async def get_allergies(patient_id: str) -> dict:
    async with get_session_factory()() as session:
        return await (await _ensure_patient(session, patient_id)).allergies(patient_id)

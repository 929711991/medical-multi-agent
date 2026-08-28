from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_current_doctor
from app.schemas.auth import DoctorIdentity
from app.api.dependencies import get_ai_job_queue
from app.schemas.diagnosis import DiagnosisCreateRequest, DiagnosisCreateResponse
from app.services.diagnosis_service import DiagnosisService

router = APIRouter(tags=["diagnosis"], dependencies=[Depends(get_current_doctor)])


@router.post("/diagnoses", response_model=DiagnosisCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_diagnosis(
    payload: DiagnosisCreateRequest,
    queue=Depends(get_ai_job_queue),
    doctor: DoctorIdentity = Depends(get_current_doctor),
) -> DiagnosisCreateResponse:
    """创建持久化病例，并在后台调度诊断图。"""
    try:
        case_id, thread_id = await DiagnosisService.create_case(
            patient_id=payload.patient_id,
            question=payload.question,
            source_channel="doctor_web",
            visit_id=payload.visit_id,
            doctor_department=doctor.department,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        await queue.enqueue_doctor_case(
            case_id=case_id,
            thread_id=thread_id,
            patient_id=payload.patient_id,
            question=payload.question,
        )
    except Exception as exc:
        from app.persistence.database import get_session_factory
        from app.persistence.repositories import CaseRepository

        async with get_session_factory()() as session:
            await CaseRepository(session).set_failed(
                case_id, stage="ai_queue", error_code="AI_QUEUE_UNAVAILABLE"
            )
        raise HTTPException(status_code=503, detail="AI 分析队列暂不可用，请稍后重试") from exc
    return DiagnosisCreateResponse(
        case_id=case_id,
        thread_id=thread_id,
        status="QUEUED",
        risk_level=None,
        draft_assessment=None,
        review_required=True,
    )

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.auth import get_current_doctor
from app.api.dependencies import get_graph
from app.schemas.diagnosis import DiagnosisCreateRequest, DiagnosisCreateResponse
from app.services.diagnosis_service import DiagnosisService

router = APIRouter(tags=["diagnosis"], dependencies=[Depends(get_current_doctor)])


@router.post("/diagnoses", response_model=DiagnosisCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_diagnosis(
    payload: DiagnosisCreateRequest,
    request: Request,
    graph=Depends(get_graph),
) -> DiagnosisCreateResponse:
    try:
        case_id, thread_id = await DiagnosisService.create_case(
            patient_id=payload.patient_id,
            question=payload.question,
            source_channel="doctor_web",
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    task = asyncio.create_task(
        DiagnosisService.run_case(
            graph=graph,
            case_id=case_id,
            thread_id=thread_id,
            patient_id=payload.patient_id,
            question=payload.question,
        )
    )
    tasks = getattr(request.app.state, "diagnosis_tasks", set())
    request.app.state.diagnosis_tasks = tasks
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return DiagnosisCreateResponse(
        case_id=case_id,
        thread_id=thread_id,
        status="RUNNING",
        risk_level=None,
        draft_assessment=None,
        review_required=True,
    )

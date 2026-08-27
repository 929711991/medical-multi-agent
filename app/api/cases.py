from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_graph
from app.graph.history import get_history
from app.persistence.database import get_session_factory
from app.persistence.repositories import CaseRepository
from app.schemas.diagnosis import CaseResponse, DiagnosisResult, HistoryResponse

router = APIRouter(tags=["cases"])


@router.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str) -> CaseResponse:
    async with get_session_factory()() as session:
        case = await CaseRepository(session).get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="未找到病例")
        assessment = case.assessments[0] if case.assessments else None
        return CaseResponse(
            id=case.id,
            patient_id=case.patient_id,
            thread_id=case.thread_id,
            question=case.question,
            status=case.status,
            risk_level=case.risk_level,
            ai_result=DiagnosisResult.model_validate(assessment.ai_result_json)
            if assessment and assessment.ai_result_json
            else None,
            doctor_result=DiagnosisResult.model_validate(assessment.doctor_result_json)
            if assessment and assessment.doctor_result_json
            else None,
            review_status=assessment.review_status if assessment else None,
            created_at=case.created_at.isoformat(),
            updated_at=case.updated_at.isoformat(),
        )


@router.get("/cases/{case_id}/history", response_model=HistoryResponse)
async def case_history(case_id: str, graph=Depends(get_graph)) -> HistoryResponse:
    async with get_session_factory()() as session:
        case = await CaseRepository(session).get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="未找到病例")
        items = await get_history(graph, case.thread_id)
        return HistoryResponse(case_id=case.id, thread_id=case.thread_id, items=items)

import logging

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command

from app.api.dependencies import get_graph
from app.graph.workflow import graph_config
from app.persistence.database import get_session_factory
from app.persistence.repositories import CaseRepository, DoctorRepository
from app.schemas.diagnosis import CaseResponse, DiagnosisResult, DoctorReviewRequest

router = APIRouter(tags=["review"])
logger = logging.getLogger(__name__)


@router.post("/cases/{case_id}/review", response_model=CaseResponse)
async def review_case(case_id: str, payload: DoctorReviewRequest, graph=Depends(get_graph)) -> CaseResponse:
    async with get_session_factory()() as session:
        repository = CaseRepository(session)
        case = await repository.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="未找到病例")
        if case.status != "PENDING_REVIEW":
            raise HTTPException(status_code=409, detail=f"病例在 {case.status} 状态下不能审核")
        if not (await DoctorRepository(session).info(payload.reviewer_id))["found"]:
            raise HTTPException(status_code=404, detail="未找到审核医生")
        try:
            result = await graph.ainvoke(Command(resume=payload.model_dump(mode="json")), graph_config(case.thread_id))
            final_raw = result.get("final_assessment")
            final = DiagnosisResult.model_validate(final_raw) if final_raw else None
            await repository.save_review(
                case_id,
                action=payload.action,
                reviewer_id=payload.reviewer_id,
                result=final.model_dump(mode="json") if final else None,
                reason=payload.reason,
            )
        except Exception as exc:
            logger.exception(
                "审核恢复执行失败",
                extra={"case_id": case_id, "thread_id": case.thread_id, "status": "error"},
            )
            raise HTTPException(status_code=503, detail=f"工作流恢复暂不可用：{type(exc).__name__}") from exc
        refreshed = await repository.get(case_id)
        assert refreshed is not None
        assessment = refreshed.assessments[0]
        return CaseResponse(
            id=refreshed.id,
            patient_id=refreshed.patient_id,
            thread_id=refreshed.thread_id,
            question=refreshed.question,
            status=refreshed.status,
            risk_level=refreshed.risk_level,
            ai_result=DiagnosisResult.model_validate(assessment.ai_result_json) if assessment.ai_result_json else None,
            doctor_result=DiagnosisResult.model_validate(assessment.doctor_result_json)
            if assessment.doctor_result_json
            else None,
            review_status=assessment.review_status,
            created_at=refreshed.created_at.isoformat(),
            updated_at=refreshed.updated_at.isoformat(),
        )

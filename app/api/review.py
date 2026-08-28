import logging

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command

from app.api.auth import get_current_doctor
from app.api.dependencies import get_graph
from app.graph.workflow import graph_config
from app.persistence.database import get_session_factory
from app.persistence.repositories import CaseRepository
from app.schemas.auth import DoctorIdentity
from app.schemas.diagnosis import CaseResponse, DiagnosisResult, DoctorReviewRequest

router = APIRouter(tags=["review"])
logger = logging.getLogger(__name__)


@router.post("/cases/{case_id}/review", response_model=CaseResponse)
async def review_case(
    case_id: str,
    payload: DoctorReviewRequest,
    graph=Depends(get_graph),
    doctor: DoctorIdentity = Depends(get_current_doctor),
) -> CaseResponse:
    """使用乐观锁保存医生审核，并恢复暂停的诊断图。"""
    async with get_session_factory()() as session:
        repository = CaseRepository(session)
        case = await repository.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="未找到病例")
        if case.status != "WAITING_REVIEW":
            raise HTTPException(status_code=409, detail=f"病例在 {case.status} 状态下不能审核")
        if not await repository.claim_review(case_id, payload.expected_version):
            raise HTTPException(status_code=409, detail="该病例已被其他医生更新，请刷新后重新查看最新结果")
        try:
            snapshot = await graph.aget_state(graph_config(case.thread_id))
            if snapshot.values.get("status") in {"FINAL", "REJECTED"}:
                result = snapshot.values
            else:
                command = payload.model_dump(mode="json", exclude={"expected_version"})
                command["reviewer_id"] = doctor.doctor_id
                result = await graph.ainvoke(Command(resume=command), graph_config(case.thread_id))
            final_raw = result.get("final_assessment")
            final = DiagnosisResult.model_validate(final_raw) if final_raw else None
            graph_review = result.get("doctor_review") or {}
            persisted_action = graph_review.get("action", payload.action)
            persisted_reviewer = graph_review.get("reviewer_id", doctor.doctor_id)
            persisted_reason = graph_review.get("reason", payload.reason)
            await repository.save_review(
                case_id,
                action=persisted_action,
                reviewer_id=persisted_reviewer,
                result=final.model_dump(mode="json") if final else None,
                reason=persisted_reason,
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
            id=str(refreshed.id),
            patient_id=str(refreshed.patient_id),
            thread_id=refreshed.thread_id,
            question=refreshed.question,
            status=refreshed.status,
            risk_level=refreshed.risk_level,
            ai_result=DiagnosisResult.model_validate(assessment.ai_result_json) if assessment.ai_result_json else None,
            doctor_result=DiagnosisResult.model_validate(assessment.doctor_result_json)
            if assessment.doctor_result_json
            else None,
            review_status=assessment.review_status,
            assessment_version=assessment.version,
            reviewer_id=str(assessment.reviewer_id) if assessment.reviewer_id is not None else None,
            review_reason=assessment.review_reason,
            created_at=refreshed.created_at.isoformat(),
            updated_at=refreshed.updated_at.isoformat(),
        )

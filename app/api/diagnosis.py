import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_graph
from app.graph.workflow import graph_config, initial_state
from app.persistence.database import get_session_factory
from app.persistence.repositories import CaseRepository
from app.schemas.diagnosis import DiagnosisCreateRequest, DiagnosisCreateResponse, DiagnosisResult
from app.services.patient_access import PatientAccessService

router = APIRouter(tags=["diagnosis"])
logger = logging.getLogger(__name__)


@router.post("/diagnoses", response_model=DiagnosisCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_diagnosis(payload: DiagnosisCreateRequest, graph=Depends(get_graph)) -> DiagnosisCreateResponse:
    case_id = str(uuid4())
    thread_id = case_id
    async with get_session_factory()() as session:
        if not await PatientAccessService(session).can_access_demo_patient(payload.patient_id):
            raise HTTPException(status_code=404, detail="未找到患者")
        repository = CaseRepository(session)
        await repository.create(
            case_id=case_id,
            patient_id=payload.patient_id,
            thread_id=thread_id,
            question=payload.question,
        )
        try:
            result = await graph.ainvoke(
                initial_state(
                    case_id=case_id,
                    thread_id=thread_id,
                    patient_id=payload.patient_id,
                    question=payload.question,
                ),
                graph_config(thread_id),
            )
            raw_draft = result.get("draft_assessment")
            if not raw_draft:
                raise RuntimeError("诊断图未生成辅助诊断草稿")
            draft = DiagnosisResult.model_validate(raw_draft)
            await repository.set_draft(case_id, draft.model_dump(mode="json"), result["risk_level"])
        except Exception as exc:
            await repository.set_status(case_id, "ERROR")
            logger.exception(
                "诊断图执行失败",
                extra={"case_id": case_id, "thread_id": thread_id, "status": "error"},
            )
            raise HTTPException(status_code=503, detail=f"诊断工作流暂不可用：{type(exc).__name__}") from exc
    return DiagnosisCreateResponse(
        case_id=case_id,
        thread_id=thread_id,
        status="PENDING_REVIEW",
        risk_level=draft.risk_level,
        draft_assessment=draft,
        review_required=True,
    )

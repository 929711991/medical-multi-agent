import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.api.auth import get_current_doctor
from app.api.dependencies import get_graph
from app.graph.history import get_history
from app.persistence.database import get_session_factory
from app.persistence.repositories import CaseRepository
from app.schemas.diagnosis import CaseResponse, DiagnosisResult, HistoryResponse
from app.schemas.auth import DoctorIdentity

router = APIRouter(tags=["cases"], dependencies=[Depends(get_current_doctor)])

NODE_LABELS = {
    "prepare": "准备患者资料",
    "risk_screening": "紧急风险筛查",
    "medical_agent": "综合医学分析",
    "specialist_router": "专科分析路由",
    "cardiology_prepare": "准备心内科资料",
    "cardiology_agent": "心内科专业分析",
    "cardiology_result": "完成心内科分析",
    "gastroenterology_prepare": "准备消化科资料",
    "gastroenterology_agent": "消化科专业分析",
    "gastroenterology_result": "完成消化科分析",
    "synthesis": "生成辅助诊断",
    "doctor_review": "医生审核",
    "finalize": "形成审核结果",
}


@router.get("/cases")
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    risk_level: str | None = None,
    search: str | None = Query(None, max_length=120),
    doctor: DoctorIdentity = Depends(get_current_doctor),
) -> dict:
    """返回当前工作区筛选后的诊断病例。"""
    async with get_session_factory()() as session:
        return await CaseRepository(session).list(
            page=page,
            page_size=page_size,
            status=status,
            risk_level=risk_level,
            search=search,
            doctor_department=doctor.department,
        )


@router.get("/cases/pending-review")
async def pending_reviews(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    doctor: DoctorIdentity = Depends(get_current_doctor),
) -> dict:
    """按照风险优先级返回等待医生审核的病例。"""
    async with get_session_factory()() as session:
        return await CaseRepository(session).list(page=page, page_size=page_size, pending_only=True, doctor_department=doctor.department)


@router.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, doctor: DoctorIdentity = Depends(get_current_doctor)) -> CaseResponse:
    """返回病例及其最新 AI 评估和医生审核状态。"""
    async with get_session_factory()() as session:
        case = await CaseRepository(session).get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="未找到病例")
        if not await CaseRepository(session).can_doctor_access(case_id, doctor.department):
            raise HTTPException(status_code=403, detail="无权访问该病例")
        assessment = case.assessments[0] if case.assessments else None
        return CaseResponse(
            id=str(case.id),
            patient_id=str(case.patient_id),
            visit_id=str(case.visit_id) if case.visit_id is not None else None,
            consultation_id=str(case.consultation_id) if case.consultation_id is not None else None,
            thread_id=case.thread_id,
            question=case.question,
            status=case.status,
            risk_level=case.risk_level,
            source_channel=case.source_channel,
            failure_stage=case.failure_stage,
            error_code=case.error_code,
            ai_result=DiagnosisResult.model_validate(assessment.ai_result_json)
            if assessment and assessment.ai_result_json
            else None,
            doctor_result=DiagnosisResult.model_validate(assessment.doctor_result_json)
            if assessment and assessment.doctor_result_json
            else None,
            review_status=assessment.review_status if assessment else None,
            assessment_version=assessment.version if assessment else 1,
            reviewer_id=str(assessment.reviewer_id) if assessment and assessment.reviewer_id is not None else None,
            review_reason=assessment.review_reason if assessment else None,
            created_at=case.created_at.isoformat(),
            updated_at=case.updated_at.isoformat(),
        )


@router.get("/cases/{case_id}/history", response_model=HistoryResponse)
async def case_history(case_id: str, graph=Depends(get_graph)) -> HistoryResponse:
    """返回病例检查点历史的安全业务摘要。"""
    async with get_session_factory()() as session:
        case = await CaseRepository(session).get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="未找到病例")
        items = await get_history(graph, case.thread_id)
        return HistoryResponse(case_id=str(case.id), thread_id=case.thread_id, items=items)


@router.get("/cases/{case_id}/events")
async def case_events(case_id: str, request: Request, graph=Depends(get_graph)) -> StreamingResponse:
    """通过服务器推送事件持续输出图进度和落库状态变化。"""
    async with get_session_factory()() as session:
        case = await CaseRepository(session).get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="未找到病例")
        thread_id = case.thread_id

    async def stream():
        """持续输出事件帧，直到病例结束或客户端断开连接。"""
        emitted: set[str] = set()
        while not await request.is_disconnected():
            try:
                items = await get_history(graph, thread_id)
                for item in reversed(items):
                    key = f"{item.checkpoint_id}:{item.stage}"
                    if item.stage == "initial" or key in emitted:
                        continue
                    emitted.add(key)
                    payload = {
                        "event": "graph.node.completed",
                        "case_id": case_id,
                        "node": item.stage,
                        "label": NODE_LABELS.get(item.stage, "处理临床信息"),
                        "status": "completed",
                        "timestamp": item.created_at,
                    }
                    yield f"event: graph.node.completed\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                async with get_session_factory()() as session:
                    current = await CaseRepository(session).get(case_id)
                if current and current.status in {"WAITING_REVIEW", "FINAL", "REJECTED", "FAILED"}:
                    payload = {"event": "case.status.changed", "case_id": case_id, "status": current.status}
                    yield f"event: case.status.changed\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break
                yield ": keep-alive\n\n"
                await asyncio.sleep(0.75)
            except Exception:
                payload = {
                    "event": "stream.unavailable",
                    "case_id": case_id,
                    "status": "failed",
                    "message": "诊断进度暂时不可用，请刷新病例状态",
                }
                yield f"event: stream.unavailable\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

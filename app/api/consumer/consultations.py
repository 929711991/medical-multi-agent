from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.api.consumer.dependencies import get_consumer_job_queue, get_current_consumer, get_rate_limiter
from app.persistence.consumer_repositories import (
    ConsultationRepository,
    ConsumerPatientRelationRepository,
)
from app.persistence.database import get_session_factory
from app.persistence.models import Consultation, ConsultationMessage, ConsumerUser
from app.core.config import get_settings
from app.services.rate_limit import RateLimitExceeded
from sqlalchemy import func, select
from app.schemas.consumer import (
    ConsultationCreateRequest,
    ConsultationMessageRequest,
    ConsultationMessageResponse,
    ConsultationResponse,
)
from app.services.consumer_access import ConsumerConsultationAccessService, ConsumerPatientAccessService
from app.services.consumer_consultation import ConsumerConsultationService, ConsultationStateMachine
from app.services.consumer_escalation import ConsumerEscalationService
from app.persistence.repositories import CaseRepository

router = APIRouter(prefix="/consultations", tags=["consumer-consultations"])


def _consultation(item: Consultation) -> ConsultationResponse:
    return ConsultationResponse(
        id=str(item.id),
        patient_id=str(item.patient_id),
        thread_id=item.thread_id,
        consultation_type=item.consultation_type,
        status=item.status,
        risk_level=item.risk_level,
        recommended_department_code=item.recommended_department_code,
        linked_case_id=str(item.linked_case_id) if item.linked_case_id else None,
        source_channel=item.source_channel,
        failure_stage=item.failure_stage,
        error_code=item.error_code,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _message(item: ConsultationMessage, duplicate: bool = False) -> ConsultationMessageResponse:
    return ConsultationMessageResponse(
        id=str(item.id),
        client_message_id=item.client_message_id,
        sender_type=item.sender_type,
        sender_id=str(item.sender_id) if item.sender_id else None,
        content_type=item.content_type,
        content=item.content,
        metadata=item.metadata_json,
        created_at=item.created_at,
        duplicate=duplicate,
    )


async def _require_access(session, user_id: str, consultation_id: str) -> Consultation:
    service = ConsumerConsultationAccessService(session)
    if not await service.can_access_consultation(user_id, consultation_id):
        raise HTTPException(status_code=403, detail="无权访问该咨询")
    item = await ConsultationRepository(session).get(consultation_id)
    assert item is not None
    return item


@router.post("", response_model=ConsultationResponse, status_code=201)
async def create_consultation(
    payload: ConsultationCreateRequest,
    user: ConsumerUser = Depends(get_current_consumer),
) -> ConsultationResponse:
    async with get_session_factory()() as session:
        if not await ConsumerPatientAccessService(session).can_access_patient(
            str(user.id), payload.patient_id, "CONTRIBUTE"
        ):
            raise HTTPException(status_code=403, detail="无权为该健康档案创建咨询")
        item = await ConsultationRepository(session).create(
            user_id=user.id,
            patient_id=payload.patient_id,
            consultation_type=payload.consultation_type,
        )
        return _consultation(item)


@router.get("", response_model=list[ConsultationResponse])
async def list_consultations(
    user: ConsumerUser = Depends(get_current_consumer),
) -> list[ConsultationResponse]:
    async with get_session_factory()() as session:
        rows = await ConsultationRepository(session).list_for_user(user.id)
        return [_consultation(item) for item in rows]


@router.get("/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(
    consultation_id: str, user: ConsumerUser = Depends(get_current_consumer)
) -> ConsultationResponse:
    async with get_session_factory()() as session:
        return _consultation(await _require_access(session, str(user.id), consultation_id))


@router.get("/{consultation_id}/messages", response_model=list[ConsultationMessageResponse])
async def list_messages(
    consultation_id: str, user: ConsumerUser = Depends(get_current_consumer)
) -> list[ConsultationMessageResponse]:
    async with get_session_factory()() as session:
        await _require_access(session, str(user.id), consultation_id)
        return [_message(item) for item in await ConsultationRepository(session).messages(consultation_id)]


@router.post("/{consultation_id}/messages")
async def post_message(
    consultation_id: str,
    payload: ConsultationMessageRequest,
    user: ConsumerUser = Depends(get_current_consumer),
    limiter=Depends(get_rate_limiter),
) -> dict:
    try:
        await limiter.check("user", str(user.id), get_settings().rate_limit_user_per_minute, 60)
        await limiter.check(
            "consultation", consultation_id, get_settings().rate_limit_consultation_per_minute, 60
        )
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail="消息发送过于频繁，请稍后再试") from exc
    async with get_session_factory()() as session:
        consultation = await _require_access(session, str(user.id), consultation_id)
        if not await ConsumerConsultationAccessService(session).can_contribute(
            str(user.id), consultation_id
        ):
            raise HTTPException(status_code=403, detail="该分享仅允许查看，不能补充咨询")
        relation = await ConsumerPatientRelationRepository(session).get(user.id, consultation.patient_id)
        sender_type = "PATIENT" if relation and relation.relation_type == "self" else "FAMILY_MEMBER"
        try:
            message, inserted, intake = await ConsumerConsultationService(session).add_user_message(
                consultation_id=consultation_id,
                user_id=str(user.id),
                client_message_id=payload.client_message_id,
                content=payload.content,
                sender_type=sender_type,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="当前咨询状态不能继续发送消息") from exc
        return {"message": _message(message, duplicate=not inserted), "intake": intake.model_dump()}


@router.post("/{consultation_id}/analyze", status_code=202)
async def analyze(
    consultation_id: str,
    queue=Depends(get_consumer_job_queue),
    user: ConsumerUser = Depends(get_current_consumer),
    limiter=Depends(get_rate_limiter),
) -> dict:
    try:
        await limiter.check("llm", str(user.id), get_settings().rate_limit_llm_per_hour, 3600)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail="AI 分析次数已达当前限额") from exc
    async with get_session_factory()() as session:
        active = await session.scalar(
            select(func.count()).select_from(Consultation).where(
                Consultation.consumer_user_id == user.id,
                Consultation.status == "ANALYZING",
            )
        ) or 0
        if active >= get_settings().max_concurrent_ai_analyses:
            raise HTTPException(status_code=429, detail="同时进行的 AI 分析过多，请等待完成")
        consultation = await _require_access(session, str(user.id), consultation_id)
        try:
            ConsultationStateMachine.validate(consultation.status, "ANALYZING")
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="预问诊信息尚未完整或当前状态不能分析") from exc
        repository = ConsultationRepository(session)
        await repository.set_status(consultation_id, "ANALYZING")
        job_id = str(uuid4())
        try:
            await queue.enqueue_consumer_analysis(
                consultation_id=consultation_id, job_id=job_id, user_id=str(user.id)
            )
        except Exception as exc:
            await repository.set_status(
                consultation_id,
                "FAILED",
                failure_stage="ai_queue",
                error_code="AI_QUEUE_UNAVAILABLE",
            )
            raise HTTPException(status_code=503, detail="AI 分析队列暂不可用，请稍后重试") from exc
        return {"consultation_id": consultation_id, "job_id": job_id, "status": "ANALYZING"}


@router.post("/{consultation_id}/escalate", status_code=202)
async def escalate(
    consultation_id: str,
    queue=Depends(get_consumer_job_queue),
    user: ConsumerUser = Depends(get_current_consumer),
) -> dict:
    async with get_session_factory()() as session:
        await _require_access(session, str(user.id), consultation_id)
        try:
            case_id, thread_id, patient_id, question, visit_id = await ConsumerEscalationService(
                session
            ).escalate(consultation_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="当前咨询状态不能转医生") from exc
        try:
            await queue.enqueue_doctor_case(
                case_id=case_id,
                thread_id=thread_id,
                patient_id=patient_id,
                question=question,
            )
        except Exception as exc:
            await CaseRepository(session).set_failed(
                case_id, stage="ai_queue", error_code="AI_QUEUE_UNAVAILABLE"
            )
            await ConsultationRepository(session).set_status(
                consultation_id,
                "FAILED",
                failure_stage="ai_queue",
                error_code="AI_QUEUE_UNAVAILABLE",
            )
            raise HTTPException(status_code=503, detail="转医生分析队列暂不可用") from exc
        return {"consultation_id": consultation_id, "case_id": case_id, "visit_id": visit_id, "status": "ESCALATED"}

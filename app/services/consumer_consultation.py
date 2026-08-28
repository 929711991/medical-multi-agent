from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.consumer_repositories import ConsultationRepository
from app.persistence.database import get_session_factory
from app.graph.workflow import graph_config, initial_state
from app.services.consumer_intake import DepartmentResolver
from app.safety.risk import screen_risk
from app.services.consumer_intake import ConsumerIntakeAgent


ALLOWED_TRANSITIONS = {
    "CREATED": {"INTAKING", "WAITING_USER", "READY_ANALYSIS", "CLOSED", "FAILED"},
    "INTAKING": {"WAITING_USER", "READY_ANALYSIS", "FAILED", "CLOSED"},
    "WAITING_USER": {"WAITING_USER", "READY_ANALYSIS", "ESCALATED", "FAILED", "CLOSED"},
    "READY_ANALYSIS": {"ANALYZING", "FAILED", "CLOSED"},
    "ANALYZING": {"ADVICE_READY", "FAILED"},
    "ADVICE_READY": {"ESCALATED", "CLOSED", "ANALYZING"},
    "ESCALATED": {"CLOSED"},
    "CLOSED": set(),
    "FAILED": {"READY_ANALYSIS", "CLOSED"},
}


class ConsultationStateMachine:
    @staticmethod
    def validate(current: str, target: str) -> None:
        if target not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError("CONSULTATION_INVALID_STATE")


class ConsumerConsultationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ConsultationRepository(session)

    async def add_user_message(
        self,
        *,
        consultation_id: str,
        user_id: str,
        client_message_id: str,
        content: str,
        sender_type: str,
    ) -> tuple[object, bool, object]:
        consultation = await self.repository.get(consultation_id)
        if consultation is None:
            raise LookupError("CONSULTATION_NOT_FOUND")
        if consultation.status in {"ANALYZING", "CLOSED", "FAILED"}:
            raise ValueError("CONSULTATION_INVALID_STATE")

        # 确定性风险筛查必须发生在任何 LLM 或异步队列操作之前。
        current_risk = screen_risk(content)
        message, inserted = await self.repository.add_message(
            consultation_id=consultation_id,
            client_message_id=client_message_id,
            sender_type=sender_type,
            sender_id=user_id,
            content=content,
            metadata={"risk_level": current_risk.level, "red_flags": current_risk.red_flags},
        )
        if not inserted:
            return message, False, ConsumerIntakeAgent.assess(
                [item.content for item in await self.repository.messages(consultation_id) if item.sender_type in {"PATIENT", "FAMILY_MEMBER"}]
            )

        messages = await self.repository.messages(consultation_id)
        intake = ConsumerIntakeAgent.assess(
            [item.content for item in messages if item.sender_type in {"PATIENT", "FAMILY_MEMBER"}]
        )
        target = "WAITING_USER" if not intake.ready_for_analysis else "READY_ANALYSIS"
        if consultation.status != target:
            ConsultationStateMachine.validate(consultation.status, target)
        await self.repository.set_status(
            consultation_id,
            target,
            risk_level=intake.risk_level,
        )
        if intake.next_question:
            await self.repository.add_message(
                consultation_id=consultation_id,
                client_message_id=f"system:{message.id}",
                sender_type="SYSTEM" if intake.risk_level == "emergency" else "AI",
                sender_id=None,
                content=intake.next_question,
                metadata={
                    "ai_generated": intake.risk_level != "emergency",
                    "information_completeness": intake.information_completeness,
                    "emergency": intake.risk_level == "emergency",
                },
            )
        return message, True, intake

    @staticmethod
    async def run_analysis_job(
        graph, consultation_id: str, job_id: str, **_: str
    ) -> bool:
        """执行共享 MedicalSupervisor/RAG/SubAgent 图并持久化安全 Consumer Advice。"""
        async with get_session_factory()() as session:
            repository = ConsultationRepository(session)
            consultation = await repository.get(consultation_id)
            if consultation is None:
                raise LookupError("CONSULTATION_NOT_FOUND")
            if consultation.status in {"ADVICE_READY", "ESCALATED", "CLOSED"}:
                return False
            if consultation.status != "ANALYZING":
                raise ValueError("CONSULTATION_INVALID_STATE")
            messages = await repository.messages(consultation_id)
            query = "\n".join(
                item.content
                for item in messages
                if item.sender_type in {"PATIENT", "FAMILY_MEMBER"}
            )
            try:
                result = await graph.ainvoke(
                    initial_state(
                        case_id=consultation_id,
                        thread_id=consultation.thread_id,
                        patient_id=str(consultation.patient_id),
                        question=query,
                    ),
                    graph_config(consultation.thread_id),
                )
                advice = result.get("consumer_advice")
                if not advice:
                    raise RuntimeError("CONSUMER_ADVICE_EMPTY")
                department = DepartmentResolver.resolve(
                    query, (result.get("draft_assessment") or {}).get("recommended_department")
                )
                await repository.add_message(
                    consultation_id=consultation_id,
                    client_message_id=f"analysis:{job_id}",
                    sender_type="AI",
                    sender_id=None,
                    content=advice["summary"],
                    metadata={"advice": advice, "ai_generated": True},
                )
                await repository.set_status(
                    consultation_id,
                    "ADVICE_READY",
                    risk_level=advice["urgency"],
                    department_code=department,
                )
                return True
            except Exception:
                await repository.set_status(
                    consultation_id,
                    "FAILED",
                    failure_stage="consumer_analysis",
                    error_code="AI_ANALYSIS_FAILED",
                )
                raise

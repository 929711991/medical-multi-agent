import logging

from app.graph.workflow import graph_config, initial_state
from app.core.snowflake import generate_snowflake_id
from app.persistence.database import get_session_factory
from app.persistence.repositories import CaseRepository
from app.schemas.diagnosis import DiagnosisResult
from app.services.patient_access import PatientAccessService

logger = logging.getLogger(__name__)


class DiagnosisService:
    @staticmethod
    async def create_case(
        *,
        patient_id: str,
        question: str,
        source_channel: str = "doctor_web",
        visit_id: str | None = None,
        consultation_id: str | None = None,
        doctor_department: str | None = None,
    ) -> tuple[str, str]:
        """校验患者访问权限并创建病例及对应图线程。"""
        # 病例编号使用雪花算法生成，数据库中的病例主键始终保持 BIGINT。
        case_id = str(generate_snowflake_id())
        thread_id = case_id
        async with get_session_factory()() as session:
            if not await PatientAccessService(session).can_access_patient(
                patient_id, doctor_department
            ):
                raise LookupError("未找到患者")
            if visit_id is not None:
                from app.persistence.repositories import PatientRepository

                if await PatientRepository(session).get_visit(patient_id, visit_id) is None:
                    raise LookupError("未找到患者本次接诊记录")
            repository = CaseRepository(session)
            await repository.create(
                case_id=case_id,
                patient_id=patient_id,
                thread_id=thread_id,
                question=question,
                source_channel=source_channel,
                visit_id=visit_id,
                consultation_id=consultation_id,
                status="QUEUED",
            )
        return case_id, thread_id

    @staticmethod
    async def run_case(*, graph, case_id: str, thread_id: str, patient_id: str, question: str) -> bool:
        """执行诊断图并把异常状态持久化到病例记录。"""
        async with get_session_factory()() as session:
            repository = CaseRepository(session)
            if not await repository.claim_ai_run(case_id):
                logger.info("忽略重复或终态 AI 病例任务", extra={"case_id": case_id})
                return False
            try:
                result = await graph.ainvoke(
                    initial_state(
                        case_id=case_id,
                        thread_id=thread_id,
                        patient_id=patient_id,
                        question=question,
                    ),
                    graph_config(thread_id),
                )
                raw_draft = result.get("draft_assessment")
                if not raw_draft:
                    raise RuntimeError("诊断图未生成辅助诊断草稿")
                draft = DiagnosisResult.model_validate(raw_draft)
                await repository.set_draft(case_id, draft.model_dump(mode="json"), result["risk_level"])
                return True
            except Exception:
                await repository.set_failed(
                    case_id, stage="diagnosis_graph", error_code="AI_ANALYSIS_FAILED"
                )
                logger.exception(
                    "诊断图执行失败",
                    extra={"case_id": case_id, "thread_id": thread_id, "status": "failed"},
                )
                raise

from app.core.snowflake import generate_snowflake_id
from app.persistence.consumer_repositories import ConsultationRepository
from app.persistence.repositories import CaseRepository, DepartmentRepository, PatientRepository
from app.services.consumer_intake import DepartmentResolver


class ConsumerEscalationService:
    """把一次 Consumer Consultation 原子转换为共享 Visit + MedicalCase。"""

    def __init__(self, session):
        self.session = session
        self.consultations = ConsultationRepository(session)

    async def escalate(self, consultation_id: str) -> tuple[str, str, str, str, str]:
        consultation = await self.consultations.get(consultation_id)
        if consultation is None:
            raise LookupError("CONSULTATION_NOT_FOUND")
        if consultation.linked_case_id is not None:
            case = await CaseRepository(self.session).get(str(consultation.linked_case_id))
            if case is None:
                raise RuntimeError("LINKED_CASE_NOT_FOUND")
            return (
                str(case.id),
                case.thread_id,
                str(case.patient_id),
                case.question,
                str(case.visit_id),
            )
        if consultation.status not in {"ADVICE_READY", "WAITING_USER"}:
            raise ValueError("CONSULTATION_INVALID_STATE")
        if consultation.status == "WAITING_USER" and consultation.risk_level != "emergency":
            raise ValueError("CONSULTATION_INVALID_STATE")

        messages = await self.consultations.messages(consultation_id)
        question = "\n".join(
            item.content
            for item in messages
            if item.sender_type in {"PATIENT", "FAMILY_MEMBER"}
        )[-4000:]
        department_code = consultation.recommended_department_code or DepartmentResolver.resolve(question)
        department = await DepartmentRepository(self.session).get_enabled(department_code)
        if department is None:
            department = await DepartmentRepository(self.session).get_enabled("GENERAL")
        if department is None:
            raise LookupError("DEPARTMENT_NOT_FOUND")

        case_id = str(generate_snowflake_id())
        thread_id = case_id
        try:
            visit = await PatientRepository(self.session).create_visit(
                patient_id=consultation.patient_id,
                department_code=department.code,
                department=department.name,
                chief_complaint=question or "用户申请转人工医生评估",
                record={
                    "source_channel": "wechat_mini_program",
                    "consultation_id": consultation_id,
                    "self_reported": True,
                },
                commit=False,
            )
            await CaseRepository(self.session).create(
                case_id=case_id,
                patient_id=str(consultation.patient_id),
                thread_id=thread_id,
                question=question or "请审核本次 Consumer 健康咨询",
                source_channel="wechat_mini_program",
                visit_id=str(visit.id),
                consultation_id=consultation_id,
                status="QUEUED",
                commit=False,
            )
            await self.consultations.link_case(consultation_id, case_id, commit=False)
            await self.session.commit()
            return case_id, thread_id, str(consultation.patient_id), question, str(visit.id)
        except Exception:
            await self.session.rollback()
            raise

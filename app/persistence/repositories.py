from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.passwords import verify_password
from app.persistence.models import (
    Allergy,
    Doctor,
    ImagingReport,
    LabResult,
    KnowledgeDocument,
    MedicalAssessment,
    MedicalCase,
    MedicalVisit,
    Medication,
    Patient,
)


class PatientRepository:
    def __init__(self, session: AsyncSession):
        """将患者数据操作绑定到当前事务会话。"""
        self.session = session

    async def exists(self, patient_id: str) -> bool:
        """判断患者业务编号是否存在。"""
        return await self._get(patient_id) is not None

    async def _get(self, patient_id: str) -> Patient | None:
        """根据稳定的对外业务编号读取患者。"""
        return await self.session.scalar(select(Patient).where(Patient.id == patient_id))

    async def data_scope(self, patient_id: str) -> str | None:
        """读取患者访问控制使用的数据隔离范围。"""
        patient = await self._get(patient_id)
        return patient.data_scope if patient else None

    async def create(
        self,
        *,
        name: str,
        birth_date: date | None,
        sex: str,
        history: list[str],
        data_scope: str = "sandbox",
        source_channel: str = "doctor_web",
    ) -> Patient:
        """创建沙箱患者，并分配低碰撞概率的业务编号。"""
        patient = Patient(
            id=f"PT-{uuid4().hex[:12].upper()}",
            display_name=name.strip(),
            birth_date=birth_date,
            sex=sex,
            summary_json={
                "history": [item.strip() for item in history if item.strip()],
                "sandbox": data_scope == "sandbox",
            },
            data_scope=data_scope,
            source_channel=source_channel,
        )
        self.session.add(patient)
        await self.session.commit()
        await self.session.refresh(patient)
        return patient

    async def update_patient(
        self,
        patient_id: str,
        *,
        name: str | None = None,
        birth_date: date | None = None,
        sex: str | None = None,
        history: list[str] | None = None,
    ) -> Patient | None:
        """患者存在时更新允许修改的档案字段。"""
        patient = await self._get(patient_id)
        if patient is None:
            return None
        if name is not None:
            patient.display_name = name.strip()
        if birth_date is not None:
            patient.birth_date = birth_date
        if sex is not None:
            patient.sex = sex
        if history is not None:
            summary = dict(patient.summary_json or {})
            summary["history"] = [item.strip() for item in history if item.strip()]
            patient.summary_json = summary
        await self.session.commit()
        await self.session.refresh(patient)
        return patient

    async def list(
        self, *, page: int = 1, page_size: int = 20, search: str | None = None, sex: str | None = None
    ) -> dict[str, Any]:
        """返回经过筛选和分页的患者工作列表。"""
        filters = [Patient.data_scope == "sandbox"]
        if search:
            term = f"%{search.strip()}%"
            filters.append(or_(Patient.id.like(term), Patient.display_name.like(term)))
        if sex:
            filters.append(Patient.sex == sex)
        total = await self.session.scalar(select(func.count()).select_from(Patient).where(*filters)) or 0
        rows = (
            await self.session.scalars(
                select(Patient)
                .where(*filters)
                .order_by(Patient.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        items: list[dict[str, Any]] = []
        today = datetime.now(UTC).date()
        for patient in rows:
            latest_visit = await self.session.scalar(
                select(MedicalVisit).where(MedicalVisit.patient_id == patient.id).order_by(MedicalVisit.visit_time.desc())
            )
            latest_case = await self.session.scalar(
                select(MedicalCase).where(MedicalCase.patient_id == patient.id).order_by(MedicalCase.updated_at.desc())
            )
            age = today.year - patient.birth_date.year - (
                (today.month, today.day) < (patient.birth_date.month, patient.birth_date.day)
            ) if patient.birth_date else None
            items.append({
                "patient_id": patient.id,
                "name": patient.display_name,
                "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
                "age": age,
                "sex": patient.sex,
                "history": patient.summary_json.get("history", []),
                "data_scope": patient.data_scope,
                "source_channel": patient.source_channel,
                "latest_visit": latest_visit.visit_time.isoformat() if latest_visit else None,
                "current_case_risk": latest_case.risk_level if latest_case and latest_case.status in {"RUNNING", "WAITING_REVIEW"} else None,
            })
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    async def summary(self, patient_id: str) -> dict[str, Any]:
        """返回 API 和 MCP 共用的标准化患者摘要。"""
        patient = await self._get(patient_id)
        if patient is None:
            return {"found": False, "patient_id": patient_id, "message": "未找到患者"}
        return {
            "found": True,
            "patient_id": patient.id,
            "display_name": patient.display_name,
            "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
            "sex": patient.sex,
            "summary": patient.summary_json,
            "data_scope": patient.data_scope,
            "source_channel": patient.source_channel,
        }

    async def visits(self, patient_id: str) -> dict[str, Any]:
        """按时间倒序返回患者就诊记录。"""
        return await self._records(
            patient_id,
            MedicalVisit,
            MedicalVisit.visit_time,
            lambda x: {
                "id": str(x.id),
                "visit_time": x.visit_time.isoformat(),
                "department": x.department,
                "chief_complaint": x.chief_complaint,
                "record": x.record_json,
            },
        )

    async def labs(self, patient_id: str) -> dict[str, Any]:
        """按时间倒序返回患者检验结果。"""
        return await self._records(
            patient_id,
            LabResult,
            LabResult.observed_at,
            lambda x: {
                "id": str(x.id),
                "observed_at": x.observed_at.isoformat(),
                "test_name": x.test_name,
                "value": x.value,
                "reference_range": x.reference_range,
                "abnormal_flag": x.abnormal_flag,
            },
        )

    async def imaging(self, patient_id: str) -> dict[str, Any]:
        """按时间倒序返回患者影像报告。"""
        return await self._records(
            patient_id,
            ImagingReport,
            ImagingReport.observed_at,
            lambda x: {
                "id": str(x.id),
                "observed_at": x.observed_at.isoformat(),
                "modality": x.modality,
                "body_part": x.body_part,
                "findings": x.findings,
                "impression": x.impression,
            },
        )

    async def medications(self, patient_id: str) -> dict[str, Any]:
        """按时间倒序返回患者用药记录。"""
        return await self._records(
            patient_id,
            Medication,
            Medication.started_at,
            lambda x: {
                "id": str(x.id),
                "name": x.name,
                "dose": x.dose,
                "route": x.route,
                "started_at": x.started_at.isoformat() if x.started_at else None,
                "ended_at": x.ended_at.isoformat() if x.ended_at else None,
            },
        )

    async def allergies(self, patient_id: str) -> dict[str, Any]:
        """按时间倒序返回患者过敏记录。"""
        return await self._records(
            patient_id,
            Allergy,
            Allergy.observed_at,
            lambda x: {
                "id": str(x.id),
                "substance": x.substance,
                "reaction": x.reaction,
                "severity": x.severity,
                "observed_at": x.observed_at.isoformat() if x.observed_at else None,
            },
        )

    async def all_records(self, patient_id: str) -> dict[str, Any]:
        """聚合 MCP 检索所需的全部临床记录类型。"""
        if not await self.exists(patient_id):
            return {"found": False, "patient_id": patient_id, "message": "未找到患者", "records": {}}
        return {
            "found": True,
            "patient_id": patient_id,
            "records": {
                "summary": await self.summary(patient_id),
                "visits": (await self.visits(patient_id))["items"],
                "labs": (await self.labs(patient_id))["items"],
                "imaging": (await self.imaging(patient_id))["items"],
                "medications": (await self.medications(patient_id))["items"],
                "allergies": (await self.allergies(patient_id))["items"],
            },
        }

    async def _records(self, patient_id: str, model: Any, order: Any, serializer: Any) -> dict[str, Any]:
        """以统一方式读取并序列化一种临床记录。"""
        if not await self.exists(patient_id):
            return {"found": False, "patient_id": patient_id, "message": "未找到患者", "items": []}
        rows = (await self.session.scalars(select(model).where(model.patient_id == patient_id).order_by(order.desc()))).all()
        return {"found": True, "patient_id": patient_id, "items": [serializer(row) for row in rows]}


class DoctorRepository:
    def __init__(self, session: AsyncSession):
        """将医生身份操作绑定到当前事务会话。"""
        self.session = session

    async def info(self, doctor_id: str) -> dict[str, Any]:
        """根据医生业务编号返回对外身份信息。"""
        doctor = await self.session.scalar(select(Doctor).where(Doctor.id == doctor_id))
        if doctor is None:
            return {"found": False, "doctor_id": doctor_id, "message": "未找到医生"}
        return {
            "found": True,
            "doctor_id": doctor.id,
            "name": doctor.name,
            "department": doctor.department,
            "title": doctor.title,
        }

    async def authenticate(self, account: str, password: str) -> dict[str, Any]:
        """使用落库账号和 PBKDF2 密码摘要验证医生身份。"""
        doctor = await self.session.scalar(select(Doctor).where(Doctor.account == account))
        if doctor is None or not verify_password(password, doctor.password_hash):
            return {"found": False, "doctor_id": account, "message": "invalid login credentials"}
        return {
            "found": True,
            "doctor_id": doctor.id,
            "account": doctor.account,
            "name": doctor.name,
            "department": doctor.department,
            "title": doctor.title,
        }


class CaseRepository:
    def __init__(self, session: AsyncSession):
        """将诊断病例操作绑定到当前事务会话。"""
        self.session = session

    async def create(
        self,
        *,
        case_id: str,
        patient_id: str,
        thread_id: str,
        question: str,
        source_channel: str = "doctor_web",
    ) -> MedicalCase:
        """在同一事务中创建病例及其初始待审核评估。"""
        case = MedicalCase(
            id=case_id,
            patient_id=patient_id,
            thread_id=thread_id,
            question=question,
            source_channel=source_channel,
        )
        case.assessments.append(MedicalAssessment(review_status="PENDING"))
        self.session.add(case)
        await self.session.commit()
        await self.session.refresh(case)
        return case

    async def get(self, case_id: str) -> MedicalCase | None:
        """根据对外病例编号读取病例及其评估。"""
        statement = select(MedicalCase).where(MedicalCase.id == case_id).options(selectinload(MedicalCase.assessments))
        return (await self.session.scalars(statement)).first()

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        risk_level: str | None = None,
        search: str | None = None,
        pending_only: bool = False,
    ) -> dict[str, Any]:
        """返回带患者展示信息的病例列表或审核队列分页。"""
        filters = []
        if pending_only:
            filters.append(MedicalCase.status == "WAITING_REVIEW")
        elif status:
            filters.append(MedicalCase.status == status)
        if risk_level:
            filters.append(MedicalCase.risk_level == risk_level)
        statement = select(MedicalCase).options(selectinload(MedicalCase.assessments))
        if search:
            term = f"%{search.strip()}%"
            statement = statement.join(Patient).where(or_(MedicalCase.id.like(term), Patient.display_name.like(term)))
        statement = statement.where(*filters)
        total_statement = select(func.count()).select_from(MedicalCase).where(*filters)
        if search:
            total_statement = total_statement.join(Patient).where(
                or_(MedicalCase.id.like(term), Patient.display_name.like(term))
            )
        total = await self.session.scalar(total_statement) or 0
        if pending_only:
            risk_order = func.field(MedicalCase.risk_level, "emergency", "high", "medium", "low")
            statement = statement.order_by(risk_order, MedicalCase.updated_at.asc())
        else:
            statement = statement.order_by(MedicalCase.updated_at.desc())
        rows = (await self.session.scalars(statement.offset((page - 1) * page_size).limit(page_size))).all()
        patient_ids = {row.patient_id for row in rows}
        patients = {
            item.id: item
            for item in (await self.session.scalars(select(Patient).where(Patient.id.in_(patient_ids)))).all()
        } if patient_ids else {}
        items = []
        for row in rows:
            assessment = row.assessments[0] if row.assessments else None
            patient = patients.get(row.patient_id)
            items.append({
                "id": row.id,
                "patient_id": row.patient_id,
                "patient_name": patient.display_name if patient else row.patient_id,
                "question": row.question,
                "status": row.status,
                "risk_level": row.risk_level,
                "specialty": _specialty_from_result(assessment.ai_result_json if assessment else None),
                "assessment_version": assessment.version if assessment else 1,
                "ai_completed_at": assessment.updated_at.isoformat() if assessment and assessment.ai_result_json else None,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            })
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    async def set_draft(self, case_id: str, result: dict[str, Any], risk_level: str) -> None:
        """保存 AI 草稿，并将病例移入医生审核队列。"""
        case = await self.get(case_id)
        if case is None:
            raise LookupError("未找到病例")
        case.status = "WAITING_REVIEW"
        case.risk_level = risk_level
        case.assessments[0].ai_result_json = result
        await self.session.commit()

    async def claim_review(self, case_id: str, expected_version: int) -> bool:
        """通过递增评估版本号获取乐观审核锁。"""
        case = await self.get(case_id)
        if case is None or case.status != "WAITING_REVIEW" or not case.assessments:
            return False
        assessment_id = case.assessments[0].id
        result = await self.session.execute(
            update(MedicalAssessment)
            .where(
                MedicalAssessment.id == assessment_id,
                MedicalAssessment.version == expected_version,
                MedicalAssessment.review_status == "PENDING",
            )
            .values(version=MedicalAssessment.version + 1)
        )
        await self.session.commit()
        return result.rowcount == 1

    async def set_status(self, case_id: str, status: str) -> None:
        """保存已有病例的工作流状态变化。"""
        case = await self.get(case_id)
        if case is None:
            raise LookupError("未找到病例")
        case.status = status
        await self.session.commit()

    async def save_review(
        self,
        case_id: str,
        *,
        action: str,
        reviewer_id: str,
        result: dict[str, Any] | None,
        reason: str | None,
    ) -> None:
        """保存医生最终结论，并完成或驳回病例。"""
        case = await self.get(case_id)
        if case is None:
            raise LookupError("未找到病例")
        assessment = case.assessments[0]
        assessment.review_status = action.upper()
        assessment.reviewer_id = reviewer_id
        assessment.doctor_result_json = result
        assessment.review_reason = reason
        assessment.reviewed_at = datetime.now(UTC)
        case.status = "REJECTED" if action == "reject" else "FINAL"
        await self.session.commit()


class KnowledgeRepository:
    def __init__(self, session: AsyncSession):
        """将知识文档状态操作绑定到当前会话。"""
        self.session = session

    async def get(self, document_id: str) -> KnowledgeDocument | None:
        """根据对外文档编号读取知识文档。"""
        return await self.session.scalar(
            select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        )

    async def count_ready(self) -> int:
        """统计已经完成向量入库的文档数量。"""
        return int(
            await self.session.scalar(
                select(func.count()).select_from(KnowledgeDocument).where(KnowledgeDocument.status == "READY")
            )
            or 0
        )

    async def list(self, *, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        """返回分页的知识文档入库状态列表。"""
        total = int(await self.session.scalar(select(func.count()).select_from(KnowledgeDocument)) or 0)
        rows = (
            await self.session.scalars(
                select(KnowledgeDocument)
                .order_by(KnowledgeDocument.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return {
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "source": item.source,
                    "source_type": item.source_type,
                    "version": item.version,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "checksum": item.checksum,
                    "status": item.status,
                    "chunk_count": item.chunk_count,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                }
                for item in rows
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    async def save_state(
        self,
        *,
        document_id: str,
        title: str,
        source: str,
        source_type: str,
        version: str | None,
        checksum: str,
        status: str,
        chunk_count: int,
    ) -> KnowledgeDocument:
        """新增或更新文档的持久化入库状态。"""
        document = await self.get(document_id)
        if document is None:
            document = KnowledgeDocument(id=document_id)
            self.session.add(document)
        document.title = title
        document.source = source
        document.source_type = source_type
        document.version = version
        document.checksum = checksum
        document.status = status
        document.chunk_count = chunk_count
        await self.session.commit()
        await self.session.refresh(document)
        return document


def _specialty_from_result(result: dict[str, Any] | None) -> str | None:
    """从结构化诊断结果中提取第一个专科标签。"""
    if not result:
        return None
    opinions = result.get("specialist_opinions") or []
    return opinions[0].get("specialty") if opinions else None

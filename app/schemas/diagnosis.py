from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.evidence import KnowledgeEvidence

RiskLevel = Literal["low", "medium", "high", "emergency"]


class PossibleCondition(BaseModel):
    name: str
    reason: str
    confidence: float = Field(ge=0, le=1)


class SpecialistOpinion(BaseModel):
    specialty: Literal["cardiology", "gastroenterology"]
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    differential_directions: list[PossibleCondition] = Field(default_factory=list)
    recommended_tests: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)


class DiagnosisResult(BaseModel):
    clinical_summary: str
    key_findings: list[str] = Field(default_factory=list)
    possible_conditions: list[PossibleCondition] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_tests: list[str] = Field(default_factory=list)
    recommended_department: str = "全科/内科"
    risk_level: RiskLevel = "low"
    specialist_opinions: list[SpecialistOpinion] = Field(default_factory=list)
    evidence: list[KnowledgeEvidence] = Field(default_factory=list)
    rag_enabled: bool = False
    disclaimer: str = "本结果仅用于医生辅助决策，不能替代医生的临床诊断。"


class DiagnosisCreateRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=3, max_length=4000)


class DiagnosisCreateResponse(BaseModel):
    case_id: str
    thread_id: str
    status: str
    risk_level: RiskLevel | None = None
    draft_assessment: DiagnosisResult | None = None
    review_required: bool = True


class DoctorReviewRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    expected_version: int = Field(ge=1)
    edited_result: DiagnosisResult | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_edit(self) -> "DoctorReviewRequest":
        """校验编辑审核动作必须携带完整的结构化诊断结果。"""
        if self.action == "edit" and self.edited_result is None:
            raise ValueError("action 为 edit 时必须提供 edited_result")
        return self


class GraphDoctorReview(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=64)
    action: Literal["approve", "edit", "reject"]
    edited_result: DiagnosisResult | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_edit(self) -> "GraphDoctorReview":
        """校验图恢复命令中的编辑结果和审核字段。"""
        if self.action == "edit" and self.edited_result is None:
            raise ValueError("action 为 edit 时必须提供 edited_result")
        return self


class CaseResponse(BaseModel):
    id: str
    patient_id: str
    thread_id: str
    question: str
    status: str
    risk_level: RiskLevel | None = None
    source_channel: str = "doctor_web"
    ai_result: DiagnosisResult | None = None
    doctor_result: DiagnosisResult | None = None
    review_status: str | None = None
    assessment_version: int = 1
    reviewer_id: str | None = None
    review_reason: str | None = None
    created_at: str
    updated_at: str


class HistoryItem(BaseModel):
    checkpoint_id: str | None = None
    created_at: str | None = None
    next_nodes: list[str] = Field(default_factory=list)
    stage: str
    risk_level: str | None = None
    status: str | None = None
    has_draft: bool = False
    has_review: bool = False


class HistoryResponse(BaseModel):
    case_id: str
    thread_id: str
    items: list[HistoryItem]

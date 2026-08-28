from pydantic import BaseModel, Field

from app.schemas.diagnosis import DiagnosisResult
from app.services.consumer_intake import DepartmentResolver


class ConsumerAdvice(BaseModel):
    urgency: str
    summary: str
    next_steps: list[str] = Field(default_factory=list)
    warning_signs: list[str] = Field(default_factory=list)
    medication_safety: list[str] = Field(default_factory=list)
    recommended_department_code: str
    ai_generated: bool = True
    disclaimer: str = "AI 生成内容仅供健康参考，不替代医生诊疗；请勿据此自行确诊或调整处方。"


class MedicationSafetyGuard:
    """阻止 Consumer 建议包含处方剂量、擅自停药或明确处方指令。"""

    UNSAFE_TERMS = ("每日", "每次", "mg", "毫克", "停用", "停药", "加量", "减量", "处方")

    @classmethod
    def sanitize(cls, suggestions: list[str]) -> list[str]:
        safe = [item for item in suggestions if not any(term in item for term in cls.UNSAFE_TERMS)]
        fallback = "如正在用药，请按原处方使用；任何加减量、停药或换药应先咨询医生或药师。"
        if len(safe) != len(suggestions) or not safe:
            safe.append(fallback)
        return list(dict.fromkeys(safe))


class ConsumerAdviceAssembler:
    @classmethod
    def assemble(cls, result: DiagnosisResult, query: str) -> ConsumerAdvice:
        department = DepartmentResolver.resolve(query, result.recommended_department)
        emergency = result.risk_level == "emergency"
        next_steps = (
            ["请立即拨打 120 或前往最近急诊，由现场医护人员评估。"]
            if emergency
            else [
                f"建议前往{result.recommended_department or '全科'}进一步评估。",
                *[f"可与医生讨论：{item}" for item in result.recommended_tests[:3]],
            ]
        )
        return ConsumerAdvice(
            urgency=result.risk_level,
            summary=result.clinical_summary,
            next_steps=next_steps,
            warning_signs=list(dict.fromkeys(result.red_flags)),
            medication_safety=MedicationSafetyGuard.sanitize([]),
            recommended_department_code=department,
        )

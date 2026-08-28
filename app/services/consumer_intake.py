from pydantic import BaseModel, Field

from app.safety.risk import screen_risk


class ConsumerIntakeResult(BaseModel):
    risk_level: str
    red_flags: list[str] = Field(default_factory=list)
    ready_for_analysis: bool
    information_completeness: int = Field(ge=0, le=100)
    missing_domains: list[str] = Field(default_factory=list)
    next_question: str | None = None


class ConsumerIntakeAgent:
    """在调用长耗时医疗 AI 前执行结构化预问诊，每轮只追问一个关键问题。"""

    DURATION_TERMS = ("小时", "天", "周", "月", "刚刚", "今天", "昨", "持续")
    SEVERITY_TERMS = ("分", "轻微", "严重", "剧烈", "越来越", "影响")
    ASSOCIATED_TERMS = ("恶心", "呕吐", "发热", "大汗", "呼吸", "腹泻", "黑便", "头晕", "没有其他")

    @classmethod
    def assess(cls, patient_messages: list[str]) -> ConsumerIntakeResult:
        text = " ".join(patient_messages).strip()
        risk = screen_risk(text)
        if risk.level == "emergency":
            return ConsumerIntakeResult(
                risk_level=risk.level,
                red_flags=risk.red_flags,
                ready_for_analysis=False,
                information_completeness=100,
                missing_domains=[],
                next_question="请立即拨打 120 或前往最近急诊，不要等待 AI 分析。",
            )
        checks = {
            "持续时间": any(term in text for term in cls.DURATION_TERMS),
            "严重程度": any(term in text for term in cls.SEVERITY_TERMS),
            "伴随症状": any(term in text for term in cls.ASSOCIATED_TERMS),
        }
        missing = [name for name, present in checks.items() if not present]
        questions = {
            "持续时间": "这种不适从什么时候开始，持续了多久？",
            "严重程度": "目前不适程度如何（0—10 分），是否越来越重？",
            "伴随症状": "是否伴有发热、恶心呕吐、呼吸困难、大汗或其他不适？",
        }
        return ConsumerIntakeResult(
            risk_level=risk.level,
            red_flags=risk.red_flags,
            ready_for_analysis=not missing,
            information_completeness=round((len(checks) - len(missing)) / len(checks) * 100),
            missing_domains=missing,
            next_question=questions[missing[0]] if missing else None,
        )


class DepartmentResolver:
    """将临床症状/智能体结果解析为稳定科室编码，不绑定接诊科室与 Specialist 路由。"""

    @staticmethod
    def resolve(text: str, recommended_department: str | None = None) -> str:
        searchable = f"{text} {recommended_department or ''}".lower()
        if any(term in searchable for term in ("胸痛", "心悸", "心内", "cardio", "血压")):
            return "CARDIOLOGY"
        if any(term in searchable for term in ("腹痛", "恶心", "呕吐", "消化", "gastro", "黑便")):
            return "GASTROENTEROLOGY"
        if any(term in searchable for term in ("头晕", "偏瘫", "神经")):
            return "NEUROLOGY"
        if any(term in searchable for term in ("咳嗽", "呼吸", "肺")):
            return "RESPIRATORY"
        if any(term in searchable for term in ("血糖", "甲状腺", "内分泌")):
            return "ENDOCRINOLOGY"
        return "GENERAL"

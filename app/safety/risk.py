from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RiskScreeningResult:
    level: Literal["low", "medium", "high", "emergency"]
    red_flags: list[str]


EMERGENCY_RULES: dict[str, tuple[str, ...]] = {
    "严重胸痛": ("剧烈胸痛", "压榨性胸痛", "胸痛伴大汗", "胸痛伴晕厥"),
    "严重呼吸困难": ("无法呼吸", "严重呼吸困难", "口唇发紫", "喘不上气"),
    "意识障碍": ("意识不清", "昏迷", "突然失去意识", "叫不醒"),
    "卒中征象": ("口角歪斜", "一侧肢体无力", "言语不清", "突发偏瘫"),
    "严重出血": ("大量呕血", "大量便血", "止不住血", "咳血不止"),
    "严重过敏": ("喉头水肿", "过敏伴呼吸困难", "全身风团伴晕厥"),
}
HIGH_RULES = ("持续胸痛", "黑便", "反复呕吐", "高热不退", "血压极高")
MEDIUM_RULES = ("胸痛", "呼吸困难", "腹痛", "腹疼", "肚子疼", "右下腹", "呕吐", "头晕")


def screen_risk(text: str) -> RiskScreeningResult:
    """根据确定性规则识别必须优先处理的紧急风险。"""
    normalized = text.lower().strip()
    red_flags = [label for label, terms in EMERGENCY_RULES.items() if any(t in normalized for t in terms)]
    if red_flags:
        return RiskScreeningResult("emergency", red_flags)
    high = [term for term in HIGH_RULES if term in normalized]
    if high:
        return RiskScreeningResult("high", high)
    medium = [term for term in MEDIUM_RULES if term in normalized]
    if medium:
        return RiskScreeningResult("medium", medium)
    return RiskScreeningResult("low", [])

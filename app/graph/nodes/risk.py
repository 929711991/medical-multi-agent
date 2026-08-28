from app.graph.state import DiagnosisState
from app.safety.risk import screen_risk


async def risk_screening_node(state: DiagnosisState) -> dict:
    """在模型分析前执行确定性的紧急风险筛查。"""
    result = screen_risk(state["user_query"])
    return {
        "current_stage": "risk_screening",
        "risk_level": result.level,
        "red_flags": result.red_flags,
    }

from app.graph.state import DiagnosisState

CARDIOLOGY_TERMS = ("胸痛", "心悸", "高血压", "心电图", "肌钙蛋白", "心脏")
GASTRO_TERMS = ("腹痛", "恶心", "呕吐", "腹泻", "黑便", "胃", "消化")


async def specialist_router_node(state: DiagnosisState) -> dict:
    """将选定的专科路由标准化后写入图状态。"""
    searchable = f"{state['user_query']} {state.get('patient_context', {})} {state.get('draft_assessment', {})}"
    cardio_score = sum(term in searchable for term in CARDIOLOGY_TERMS)
    gastro_score = sum(term in searchable for term in GASTRO_TERMS)
    if cardio_score > gastro_score and cardio_score:
        intent = "cardiology"
    elif gastro_score and gastro_score >= cardio_score:
        intent = "gastroenterology"
    else:
        intent = "none"
    return {"current_stage": "specialist_router", "intent": intent}


def route_specialist(state: DiagnosisState) -> str:
    """选择专科分支，普通病例则跳过专科分析。"""
    return state.get("intent", "none")

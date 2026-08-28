from app.graph.state import DiagnosisState


async def prepare_node(state: DiagnosisState) -> dict:
    """在临床分析开始前初始化临时状态字段。"""
    return {
        "current_stage": "prepare",
        "patient_context": {"patient_id": state["patient_id"], "source": "等待 MCP 获取"},
        "specialist_opinions": [],
        "rag_evidence": [],
        "errors": [],
        "status": "RUNNING",
    }

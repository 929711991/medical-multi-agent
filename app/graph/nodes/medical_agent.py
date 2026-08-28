import json
from collections.abc import Awaitable, Callable
from typing import Any

from app.agents.medical import create_consumer_medical_supervisor, create_medical_supervisor
from app.graph.state import DiagnosisState
from app.mcp.client import get_mcp_manager
from app.schemas.diagnosis import DiagnosisResult

MedicalRunner = Callable[[DiagnosisState, dict[str, Any]], Awaitable[DiagnosisResult]]
RecordLoader = Callable[[str], Awaitable[dict[str, Any]]]


async def run_medical_supervisor(state: DiagnosisState, patient_context: dict[str, Any]) -> DiagnosisResult:
    """调用综合医学智能体，基于患者事实形成结构化诊断结果。"""
    tools = await get_mcp_manager().get_tools()
    agent = create_medical_supervisor(tools)
    prompt = {
        "patient_id": state["patient_id"],
        "doctor_question": state["user_query"],
        "deterministic_risk_level": state["risk_level"],
        "deterministic_red_flags": state["red_flags"],
        "prefetched_mcp_context": patient_context,
    }
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False, default=str)}]}
    )
    result = response.get("structured_response")
    if isinstance(result, DiagnosisResult):
        return result
    return DiagnosisResult.model_validate(result)


async def load_records_from_mcp(patient_id: str) -> dict[str, Any]:
    """通过 MCP 读取患者临床记录，并转换为图节点可用的上下文。"""
    return await get_mcp_manager().invoke_structured(
        "get_medical_records", {"patient_id": patient_id}
    )


async def run_consumer_medical_supervisor(
    state: DiagnosisState, patient_context: dict[str, Any]
) -> DiagnosisResult:
    """以只读 MCP 权限运行 Consumer MedicalSupervisor。"""
    tools = await get_mcp_manager().get_tools()
    agent = create_consumer_medical_supervisor(tools)
    prompt = {
        "patient_id": state["patient_id"],
        "user_description": state["user_query"],
        "deterministic_risk_level": state["risk_level"],
        "deterministic_red_flags": state["red_flags"],
        "prefetched_mcp_context": patient_context,
    }
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False, default=str)}]}
    )
    value = response.get("structured_response")
    return value if isinstance(value, DiagnosisResult) else DiagnosisResult.model_validate(value)


def make_medical_node(runner: MedicalRunner | None = None, record_loader: RecordLoader | None = None):
    """构造可注入测试依赖的综合医学图节点。"""
    selected_runner = runner or run_medical_supervisor
    selected_loader = record_loader or load_records_from_mcp

    async def medical_agent_node(state: DiagnosisState) -> dict:
        """加载患者事实并执行综合医学分析。"""
        context = await selected_loader(state["patient_id"])
        result = await selected_runner(state, context)
        if state["risk_level"] == "emergency" and result.risk_level != "emergency":
            result = result.model_copy(
                update={"risk_level": "emergency", "red_flags": list(set(result.red_flags + state["red_flags"]))}
            )
        return {
            "current_stage": "medical_agent",
            "patient_context": context,
            "draft_assessment": result.model_dump(mode="json"),
            "rag_evidence": [item.model_dump(mode="json") for item in result.evidence],
        }

    return medical_agent_node

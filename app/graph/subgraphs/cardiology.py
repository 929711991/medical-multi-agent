import json
from collections.abc import Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from app.agents.cardiology import create_cardiology_agent
from app.graph.state import DiagnosisState
from app.schemas.diagnosis import SpecialistOpinion

SpecialistRunner = Callable[[DiagnosisState], Awaitable[SpecialistOpinion]]


async def run_cardiology_agent(state: DiagnosisState) -> SpecialistOpinion:
    """运行心内科智能体并返回结构化专科意见。"""
    agent = create_cardiology_agent()
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": json.dumps(state["specialist_context"], ensure_ascii=False)}]}
    )
    value = response.get("structured_response")
    return value if isinstance(value, SpecialistOpinion) else SpecialistOpinion.model_validate(value)


def build_cardiology_subgraph(runner: SpecialistRunner | None = None):
    """构建可替换运行器的心内科分析子图。"""
    selected = runner or run_cardiology_agent

    async def prepare_specialist_context(state: DiagnosisState) -> dict:
        """整理心内科分析所需的患者和综合医学上下文。"""
        return {
            "current_stage": "cardiology_prepare",
            "specialist_context": {
                "specialty": "cardiology",
                "query": state["user_query"],
                "patient_facts": state["patient_context"],
                "risk": state["risk_level"],
                "draft": state["draft_assessment"],
            },
        }

    async def specialist_agent(state: DiagnosisState) -> dict:
        """调用心内科运行器生成专科意见。"""
        result = await selected(state)
        return {"current_stage": "cardiology_agent", "specialist_result": result.model_dump(mode="json")}

    async def specialist_result(state: DiagnosisState) -> dict:
        """把心内科意见写回统一图状态。"""
        return {
            "current_stage": "cardiology_result",
            "specialist_opinions": [*state.get("specialist_opinions", []), state["specialist_result"]],
        }

    graph = StateGraph(DiagnosisState)
    graph.add_node("prepare_specialist_context", prepare_specialist_context)
    graph.add_node("specialist_agent", specialist_agent)
    graph.add_node("specialist_result", specialist_result)
    graph.add_edge(START, "prepare_specialist_context")
    graph.add_edge("prepare_specialist_context", "specialist_agent")
    graph.add_edge("specialist_agent", "specialist_result")
    graph.add_edge("specialist_result", END)
    return graph.compile()

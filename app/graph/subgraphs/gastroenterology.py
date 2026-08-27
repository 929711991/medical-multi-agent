import json
from collections.abc import Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from app.agents.gastroenterology import create_gastroenterology_agent
from app.graph.state import DiagnosisState
from app.schemas.diagnosis import SpecialistOpinion

SpecialistRunner = Callable[[DiagnosisState], Awaitable[SpecialistOpinion]]


async def run_gastroenterology_agent(state: DiagnosisState) -> SpecialistOpinion:
    agent = create_gastroenterology_agent()
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": json.dumps(state["specialist_context"], ensure_ascii=False)}]}
    )
    value = response.get("structured_response")
    return value if isinstance(value, SpecialistOpinion) else SpecialistOpinion.model_validate(value)


def build_gastroenterology_subgraph(runner: SpecialistRunner | None = None):
    selected = runner or run_gastroenterology_agent

    async def prepare_specialist_context(state: DiagnosisState) -> dict:
        return {
            "current_stage": "gastroenterology_prepare",
            "specialist_context": {
                "specialty": "gastroenterology",
                "query": state["user_query"],
                "patient_facts": state["patient_context"],
                "risk": state["risk_level"],
                "draft": state["draft_assessment"],
            },
        }

    async def specialist_agent(state: DiagnosisState) -> dict:
        result = await selected(state)
        return {"current_stage": "gastroenterology_agent", "specialist_result": result.model_dump(mode="json")}

    async def specialist_result(state: DiagnosisState) -> dict:
        return {
            "current_stage": "gastroenterology_result",
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


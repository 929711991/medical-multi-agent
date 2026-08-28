from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.core.observability import observed_node
from app.graph.nodes.medical_agent import MedicalRunner, RecordLoader, make_medical_node, run_consumer_medical_supervisor
from app.graph.nodes.prepare import prepare_node
from app.graph.nodes.risk import risk_screening_node
from app.graph.nodes.specialist import route_specialist, specialist_router_node
from app.graph.nodes.synthesis import synthesis_node
from app.graph.state import DiagnosisState
from app.graph.subgraphs.cardiology import SpecialistRunner as CardiologyRunner
from app.graph.subgraphs.cardiology import build_cardiology_subgraph
from app.graph.subgraphs.gastroenterology import SpecialistRunner as GastroRunner
from app.graph.subgraphs.gastroenterology import build_gastroenterology_subgraph
from app.schemas.diagnosis import DiagnosisResult
from app.services.consumer_advice import ConsumerAdviceAssembler


async def consumer_advice_node(state: DiagnosisState) -> dict:
    result = DiagnosisResult.model_validate(state["draft_assessment"])
    advice = ConsumerAdviceAssembler.assemble(result, state["user_query"])
    return {
        "current_stage": "consumer_advice",
        "consumer_advice": advice.model_dump(mode="json"),
        "status": "ADVICE_READY",
    }


def build_consumer_consultation_graph(
    *,
    checkpointer: BaseCheckpointSaver,
    medical_runner: MedicalRunner | None = None,
    record_loader: RecordLoader | None = None,
    cardiology_runner: CardiologyRunner | None = None,
    gastroenterology_runner: GastroRunner | None = None,
):
    """复用正式医疗核心，但以 Consumer Advice 结束而非进入 Doctor HITL。"""
    workflow = StateGraph(DiagnosisState)
    workflow.add_node("prepare", observed_node("consumer_prepare", prepare_node))
    workflow.add_node("risk_screening", observed_node("consumer_risk", risk_screening_node))
    workflow.add_node(
        "medical_agent",
        observed_node(
            "consumer_medical_agent",
            make_medical_node(medical_runner or run_consumer_medical_supervisor, record_loader),
        ),
    )
    workflow.add_node("specialist_router", specialist_router_node)
    workflow.add_node("cardiology_subgraph", build_cardiology_subgraph(cardiology_runner))
    workflow.add_node("gastroenterology_subgraph", build_gastroenterology_subgraph(gastroenterology_runner))
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("consumer_advice", consumer_advice_node)
    workflow.add_edge(START, "prepare")
    workflow.add_edge("prepare", "risk_screening")
    workflow.add_edge("risk_screening", "medical_agent")
    workflow.add_edge("medical_agent", "specialist_router")
    workflow.add_conditional_edges(
        "specialist_router",
        route_specialist,
        {
            "cardiology": "cardiology_subgraph",
            "gastroenterology": "gastroenterology_subgraph",
            "none": "synthesis",
        },
    )
    workflow.add_edge("cardiology_subgraph", "synthesis")
    workflow.add_edge("gastroenterology_subgraph", "synthesis")
    workflow.add_edge("synthesis", "consumer_advice")
    workflow.add_edge("consumer_advice", END)
    return workflow.compile(checkpointer=checkpointer)

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.core.observability import observed_node
from app.graph.nodes.finalize import finalize_node
from app.graph.nodes.medical_agent import MedicalRunner, RecordLoader, make_medical_node
from app.graph.nodes.prepare import prepare_node
from app.graph.nodes.review import doctor_review_node
from app.graph.nodes.risk import risk_screening_node
from app.graph.nodes.specialist import route_specialist, specialist_router_node
from app.graph.nodes.synthesis import synthesis_node
from app.graph.state import DiagnosisState
from app.graph.subgraphs.cardiology import SpecialistRunner as CardiologyRunner
from app.graph.subgraphs.cardiology import build_cardiology_subgraph
from app.graph.subgraphs.gastroenterology import SpecialistRunner as GastroRunner
from app.graph.subgraphs.gastroenterology import build_gastroenterology_subgraph


def build_diagnosis_graph(
    *,
    checkpointer: BaseCheckpointSaver,
    medical_runner: MedicalRunner | None = None,
    record_loader: RecordLoader | None = None,
    cardiology_runner: CardiologyRunner | None = None,
    gastroenterology_runner: GastroRunner | None = None,
):
    """编译诊断工作流及其专科子图。"""
    workflow = StateGraph(DiagnosisState)
    workflow.add_node("prepare", observed_node("prepare", prepare_node))
    workflow.add_node("risk_screening", observed_node("risk_screening", risk_screening_node))
    workflow.add_node(
        "medical_agent",
        observed_node("medical_agent", make_medical_node(medical_runner, record_loader)),
    )
    workflow.add_node("specialist_router", observed_node("specialist_router", specialist_router_node))
    workflow.add_node("cardiology_subgraph", build_cardiology_subgraph(cardiology_runner))
    workflow.add_node("gastroenterology_subgraph", build_gastroenterology_subgraph(gastroenterology_runner))
    workflow.add_node("synthesis", observed_node("synthesis", synthesis_node))
    workflow.add_node("doctor_review", observed_node("doctor_review", doctor_review_node))
    workflow.add_node("finalize", observed_node("finalize", finalize_node))

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
    workflow.add_edge("synthesis", "doctor_review")
    workflow.add_edge("doctor_review", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile(checkpointer=checkpointer)


def initial_state(*, case_id: str, thread_id: str, patient_id: str, question: str) -> DiagnosisState:
    """为新的诊断任务创建标准化初始状态。"""
    return {
        "case_id": case_id,
        "thread_id": thread_id,
        "patient_id": patient_id,
        "user_query": question,
        "errors": [],
        "messages": [],
    }


def graph_config(thread_id: str) -> dict[str, Any]:
    """为持久化线程生成 LangGraph 检查点配置。"""
    return {"configurable": {"thread_id": thread_id}}

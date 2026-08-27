from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


class DiagnosisState(TypedDict, total=False):
    case_id: str
    thread_id: str
    patient_id: str
    user_query: str
    intent: Literal["cardiology", "gastroenterology", "none"]
    current_stage: str
    patient_context: dict[str, Any]
    risk_level: Literal["low", "medium", "high", "emergency"]
    red_flags: list[str]
    rag_evidence: list[dict[str, Any]]
    draft_assessment: dict[str, Any]
    specialist_opinions: list[dict[str, Any]]
    specialist_context: dict[str, Any]
    specialist_result: dict[str, Any]
    doctor_review: dict[str, Any]
    final_assessment: dict[str, Any] | None
    status: str
    errors: list[str]
    messages: Annotated[list[Any], add_messages]

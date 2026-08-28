from langgraph.types import interrupt

from app.graph.state import DiagnosisState
from app.schemas.diagnosis import GraphDoctorReview


async def doctor_review_node(state: DiagnosisState) -> dict:
    """暂停诊断图，等待医生通过、编辑或驳回。"""
    payload = {
        "type": "doctor_review_required",
        "case_id": state["case_id"],
        "thread_id": state["thread_id"],
        "risk_level": state["risk_level"],
        "red_flags": state["red_flags"],
        "draft_assessment": state["draft_assessment"],
        "allowed_actions": ["approve", "edit", "reject"],
    }
    resumed = interrupt(payload)
    review = GraphDoctorReview.model_validate(resumed)
    return {"current_stage": "doctor_review", "doctor_review": review.model_dump(mode="json")}

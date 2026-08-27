from app.graph.state import DiagnosisState


async def finalize_node(state: DiagnosisState) -> dict:
    review = state["doctor_review"]
    action = review["action"]
    if action == "reject":
        return {"current_stage": "finalize", "final_assessment": None, "status": "REJECTED"}
    if action == "edit":
        final = review["edited_result"]
    else:
        final = state["draft_assessment"]
    return {"current_stage": "finalize", "final_assessment": final, "status": "FINAL"}

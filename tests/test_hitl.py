import pytest
from langgraph.types import Command

from app.graph.history import get_history
from app.graph.workflow import build_diagnosis_graph, graph_config, initial_state
from app.schemas.diagnosis import DiagnosisResult
from tests.conftest import fake_cardiology, fake_gastro, fake_medical, fake_records, make_test_graph


async def _interrupt(graph, thread_id: str):
    result = await graph.ainvoke(
        initial_state(case_id=thread_id, thread_id=thread_id, patient_id="DEMO-P", question="轻微鼻塞，无发热"),
        graph_config(thread_id),
    )
    state = await graph.aget_state(graph_config(thread_id))
    assert state.next == ("doctor_review",)
    assert result["status"] == "WAITING_REVIEW"
    return result


@pytest.mark.asyncio
async def test_approve_resume_and_history() -> None:
    graph, _ = make_test_graph()
    draft = await _interrupt(graph, "approve")
    result = await graph.ainvoke(
        Command(resume={"reviewer_id": "DEMO-D", "action": "approve"}), graph_config("approve")
    )
    assert result["status"] == "FINAL"
    assert result["final_assessment"] == draft["draft_assessment"]
    history = await get_history(graph, "approve")
    assert len(history) >= 5
    assert any(item.has_review for item in history)


@pytest.mark.asyncio
async def test_edit_resume() -> None:
    graph, _ = make_test_graph()
    draft = await _interrupt(graph, "edit")
    edited = DiagnosisResult.model_validate(draft["draft_assessment"]).model_copy(
        update={"clinical_summary": "医生修改后的摘要"}
    )
    result = await graph.ainvoke(
        Command(
            resume={
                "reviewer_id": "DEMO-D",
                "action": "edit",
                "edited_result": edited.model_dump(mode="json"),
                "reason": "结合查体修订",
            }
        ),
        graph_config("edit"),
    )
    assert result["final_assessment"]["clinical_summary"] == "医生修改后的摘要"


@pytest.mark.asyncio
async def test_reject_resume() -> None:
    graph, _ = make_test_graph()
    await _interrupt(graph, "reject")
    result = await graph.ainvoke(
        Command(resume={"reviewer_id": "DEMO-D", "action": "reject", "reason": "信息不足"}),
        graph_config("reject"),
    )
    assert result["status"] == "REJECTED"
    assert result["final_assessment"] is None


@pytest.mark.asyncio
async def test_rebuild_graph_can_resume_same_checkpoint() -> None:
    first_graph, saver = make_test_graph()
    await _interrupt(first_graph, "restart")
    rebuilt = build_diagnosis_graph(
        checkpointer=saver,
        record_loader=fake_records,
        medical_runner=fake_medical,
        cardiology_runner=fake_cardiology,
        gastroenterology_runner=fake_gastro,
    )
    result = await rebuilt.ainvoke(
        Command(resume={"reviewer_id": "DEMO-D", "action": "approve"}), graph_config("restart")
    )
    assert result["status"] == "FINAL"

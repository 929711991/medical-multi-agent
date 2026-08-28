import pytest

from app.graph.workflow import graph_config, initial_state
from tests.conftest import make_test_graph


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "intent", "specialty"),
    [
        ("活动后胸痛并有高血压史", "cardiology", "cardiology"),
        ("上腹痛伴恶心呕吐", "gastroenterology", "gastroenterology"),
    ],
)
async def test_specialist_routes(question: str, intent: str, specialty: str) -> None:
    graph, _ = make_test_graph()
    thread_id = f"thread-{intent}"
    result = await graph.ainvoke(
        initial_state(case_id=thread_id, thread_id=thread_id, patient_id="DEMO-P", question=question),
        graph_config(thread_id),
    )
    assert result["status"] == "WAITING_REVIEW"
    assert result["intent"] == intent
    assert result["specialist_opinions"][0]["specialty"] == specialty
    assert result["final_assessment"] if "final_assessment" in result else True


@pytest.mark.asyncio
async def test_none_route() -> None:
    graph, _ = make_test_graph()
    result = await graph.ainvoke(
        initial_state(case_id="low", thread_id="low", patient_id="DEMO-P", question="轻微鼻塞，无发热"),
        graph_config("low"),
    )
    assert result["intent"] == "none"
    assert result["specialist_opinions"] == []


@pytest.mark.asyncio
async def test_emergency_rule_overrides_model_risk() -> None:
    graph, _ = make_test_graph()
    result = await graph.ainvoke(
        initial_state(case_id="em", thread_id="em", patient_id="DEMO-P", question="压榨性胸痛伴大汗"),
        graph_config("em"),
    )
    assert result["risk_level"] == "emergency"
    assert result["draft_assessment"]["risk_level"] == "emergency"

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.graph.workflow import build_diagnosis_graph
from app.main import create_app
from tests.conftest import fake_cardiology, fake_gastro, fake_medical, fake_records


def _test_app():
    graph = build_diagnosis_graph(
        checkpointer=InMemorySaver(),
        record_loader=fake_records,
        medical_runner=fake_medical,
        cardiology_runner=fake_cardiology,
        gastroenterology_runner=fake_gastro,
    )
    return create_app(graph=graph)


@pytest.mark.asyncio
async def test_health_without_external_calls() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_test_app()), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_create_review_and_history() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_test_app()), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/diagnoses",
            json={"patient_id": "DEMO-P-CARDIO", "question": "活动后胸痛并有高血压史"},
        )
        assert created.status_code == 202, created.text
        case_id = created.json()["case_id"]
        reviewed = await client.post(
            f"/api/v1/cases/{case_id}/review",
            json={"reviewer_id": "DEMO-D-001", "action": "approve"},
        )
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["status"] == "FINAL"
        history = await client.get(f"/api/v1/cases/{case_id}/history")
        assert history.status_code == 200
        assert len(history.json()["items"]) >= 5

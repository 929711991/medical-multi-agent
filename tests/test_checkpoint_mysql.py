from uuid import uuid4

import pytest
from langgraph.types import Command

from app.graph.history import get_history
from app.graph.workflow import build_diagnosis_graph, graph_config, initial_state
from app.persistence.checkpoint import mysql_checkpointer
from tests.conftest import fake_cardiology, fake_gastro, fake_medical, fake_records


def _graph(checkpointer):
    return build_diagnosis_graph(
        checkpointer=checkpointer,
        record_loader=fake_records,
        medical_runner=fake_medical,
        cardiology_runner=fake_cardiology,
        gastroenterology_runner=fake_gastro,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_checkpoint_survives_reconnect_and_has_history() -> None:
    thread_id = f"mysql-{uuid4()}"
    async with mysql_checkpointer() as first_saver:
        first_graph = _graph(first_saver)
        result = await first_graph.ainvoke(
            initial_state(
                case_id=thread_id,
                thread_id=thread_id,
                patient_id="DEMO-P-CARDIO",
                question="活动后胸痛并有高血压史",
            ),
            graph_config(thread_id),
        )
        assert result["status"] == "PENDING_REVIEW"
        state = await first_graph.aget_state(graph_config(thread_id))
        assert state.next == ("doctor_review",)

    # 新建数据库连接并重新编译图，用来模拟应用进程重启。
    async with mysql_checkpointer() as second_saver:
        restarted_graph = _graph(second_saver)
        result = await restarted_graph.ainvoke(
            Command(resume={"reviewer_id": "DEMO-D-001", "action": "approve"}),
            graph_config(thread_id),
        )
        assert result["status"] == "FINAL"
        history = await get_history(restarted_graph, thread_id)
        assert len(history) >= 5
        assert any(item.stage == "risk_screening" for item in history)
        assert any(item.has_review for item in history)

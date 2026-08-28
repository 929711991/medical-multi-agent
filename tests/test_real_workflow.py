from uuid import uuid4

import pytest

from app.graph.workflow import build_diagnosis_graph, graph_config, initial_state
from app.persistence.checkpoint import mysql_checkpointer


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_llm_mcp_graph_reaches_doctor_review() -> None:
    """使用真实 LLM、MCP 和 MySQL Checkpoint 验证生产诊断图。"""
    thread_id = f"real-{uuid4()}"
    async with mysql_checkpointer() as checkpointer:
        graph = build_diagnosis_graph(checkpointer=checkpointer)
        result = await graph.ainvoke(
            initial_state(
                case_id=thread_id,
                thread_id=thread_id,
                patient_id="DEMO-P-CARDIO",
                question="DEMO 患者活动后胸痛两天，有高血压史，请提供辅助诊断意见。",
            ),
            graph_config(thread_id),
        )
        assert result["status"] == "PENDING_REVIEW"
        assert result["intent"] == "cardiology"
        assert result["draft_assessment"]

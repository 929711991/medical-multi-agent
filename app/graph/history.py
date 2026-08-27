from typing import Any

from app.graph.workflow import graph_config
from app.schemas.diagnosis import HistoryItem


async def get_history(graph: Any, thread_id: str) -> list[HistoryItem]:
    items: list[HistoryItem] = []
    async for snapshot in graph.aget_state_history(graph_config(thread_id)):
        values = snapshot.values or {}
        checkpoint_id = snapshot.config.get("configurable", {}).get("checkpoint_id")
        items.append(
            HistoryItem(
                checkpoint_id=checkpoint_id,
                created_at=snapshot.created_at,
                next_nodes=list(snapshot.next),
                stage=values.get("current_stage", "initial"),
                risk_level=values.get("risk_level"),
                status=values.get("status"),
                has_draft=bool(values.get("draft_assessment")),
                has_review=bool(values.get("doctor_review")),
            )
        )
    return items


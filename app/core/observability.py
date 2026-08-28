import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from langgraph.errors import GraphInterrupt

from app.graph.state import DiagnosisState

logger = logging.getLogger("medical.graph")


def observed_node(name: str, node: Callable[[DiagnosisState], Awaitable[dict[str, Any]]]):
    """为图节点增加统一耗时和执行状态日志，不记录完整病历内容。"""

    async def wrapped(state: DiagnosisState) -> dict[str, Any]:
        """统计单个图节点调用耗时，并附加安全的结构化上下文。"""
        started = perf_counter()
        status = "成功"
        try:
            return await node(state)
        except GraphInterrupt:
            status = "等待医生审核"
            raise
        except Exception:
            status = "失败"
            raise
        finally:
            logger.info(
                "诊断图节点执行完成",
                extra={
                    "case_id": state.get("case_id"),
                    "thread_id": state.get("thread_id"),
                    "graph_node": name,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                    "status": status,
                },
            )

    return wrapped

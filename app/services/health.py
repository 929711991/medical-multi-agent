import asyncio
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.llm import get_llm
from app.mcp.client import get_mcp_manager
from app.persistence.database import check_mysql_ready, get_session_factory
from app.persistence.repositories import KnowledgeRepository
from app.rag.embedding import embed_query
from app.rag.redis_store import has_index, health as redis_health
from app.services.job_queue import RedisJobQueue


async def _check_checkpoint() -> bool:
    """检查 LangGraph MySQL 检查点服务是否可连接。"""
    engine = create_async_engine(get_settings().checkpoint_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


async def _check_mcp() -> bool:
    """检查患者 MCP 服务是否能返回工具列表。"""
    try:
        tools = await asyncio.wait_for(get_mcp_manager().get_tools(), timeout=10)
        names = {item.name for item in tools}
        return "get_medical_records" in names and "update_patient" in names
    except Exception:
        return False


async def _check_llm() -> bool:
    """检查真实大模型配置和轻量连接状态。"""
    settings = get_settings()
    if not settings.aliyun_llm_api_key:
        return False
    try:
        response = await asyncio.wait_for(get_llm().ainvoke("健康检查。仅回复 OK。"), timeout=15)
        return bool(getattr(response, "content", None))
    except Exception:
        return False


async def _check_rag() -> tuple[bool, bool, bool, bool, int]:
    """检查 Redis 向量索引、向量模型和已就绪文档数量。"""
    settings = get_settings()
    if not settings.rag_enabled:
        return False, False, False, False, 0
    redis_ready = await redis_health()
    if not redis_ready:
        return False, False, False, False, 0
    index_ready = await has_index()
    async with get_session_factory()() as session:
        document_count = await KnowledgeRepository(session).count_ready()
    embedding_ready = False
    if settings.embedding_model and settings.embedding_api_key:
        try:
            vector = await asyncio.wait_for(embed_query("医学知识库健康检查"), timeout=15)
            embedding_ready = bool(vector)
        except Exception:
            embedding_ready = False
    return (
        bool(index_ready and embedding_ready and document_count > 0),
        redis_ready,
        index_ready,
        embedding_ready,
        document_count,
    )


async def _check_job_queue() -> tuple[bool, bool]:
    queue = RedisJobQueue()
    try:
        await queue.ensure_group()
        queue_ready = bool(await queue.redis.ping())
        worker_ready = await queue.worker_ready()
        return queue_ready, worker_ready
    except Exception:
        return False, False
    finally:
        await queue.close()


async def collect_health() -> dict[str, Any]:
    """汇总数据库、检查点、MCP、大模型和 RAG 健康状态。"""
    settings = get_settings()
    mysql_ready, checkpoint_ready, mcp_ready, llm_ready, rag, job = await asyncio.gather(
        check_mysql_ready(),
        _check_checkpoint(),
        _check_mcp(),
        _check_llm(),
        _check_rag(),
        _check_job_queue(),
    )
    rag_ready, redis_ready, index_ready, embedding_ready, document_count = rag
    queue_ready, worker_ready = job
    critical = [mysql_ready, checkpoint_ready, mcp_ready, llm_ready, queue_ready, worker_ready]
    if settings.rag_required:
        critical.append(rag_ready)
    status = "ok" if all(critical) else "degraded" if mysql_ready else "down"
    return {
        "status": status,
        "service": settings.app_name,
        "mysql": "ready" if mysql_ready else "down",
        "checkpoint": "ready" if checkpoint_ready else "down",
        "mcp": "ready" if mcp_ready else "down",
        "mcp_configured": bool(settings.mcp_server_url),
        "llm": "ready" if llm_ready else "down",
        "llm_configured": bool(settings.aliyun_llm_api_key),
        "rag_enabled": settings.rag_enabled,
        "rag_required": settings.rag_required,
        "rag_ready": rag_ready,
        "redis": "ready" if redis_ready else "down",
        "redis_vector_ready": index_ready,
        "embedding_configured": bool(settings.embedding_model and settings.embedding_api_key),
        "embedding_ready": embedding_ready,
        "ai_queue": "ready" if queue_ready else "down",
        "ai_worker": "ready" if worker_ready else "down",
        "knowledge_documents": document_count,
    }

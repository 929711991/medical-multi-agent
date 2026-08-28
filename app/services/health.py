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
from app.rag.milvus import has_collection, health as milvus_health


async def _check_checkpoint() -> bool:
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
    try:
        tools = await asyncio.wait_for(get_mcp_manager().get_tools(), timeout=10)
        names = {item.name for item in tools}
        return "get_medical_records" in names and "update_patient" in names
    except Exception:
        return False


async def _check_llm() -> bool:
    settings = get_settings()
    if not settings.aliyun_llm_api_key:
        return False
    try:
        response = await asyncio.wait_for(get_llm().ainvoke("健康检查。仅回复 OK。"), timeout=15)
        return bool(getattr(response, "content", None))
    except Exception:
        return False


async def _check_rag() -> tuple[bool, bool, int]:
    settings = get_settings()
    if not settings.rag_enabled:
        return False, False, 0
    milvus_ready = await milvus_health()
    if not milvus_ready:
        return False, False, 0
    collection_ready = await has_collection()
    async with get_session_factory()() as session:
        document_count = await KnowledgeRepository(session).count_ready()
    embedding_ready = False
    if settings.embedding_model and settings.embedding_api_key:
        try:
            vector = await asyncio.wait_for(embed_query("医学知识库健康检查"), timeout=15)
            embedding_ready = bool(vector)
        except Exception:
            embedding_ready = False
    return bool(collection_ready and embedding_ready and document_count > 0), milvus_ready, document_count


async def collect_health() -> dict[str, Any]:
    settings = get_settings()
    mysql_ready, checkpoint_ready, mcp_ready, llm_ready, rag = await asyncio.gather(
        check_mysql_ready(),
        _check_checkpoint(),
        _check_mcp(),
        _check_llm(),
        _check_rag(),
    )
    rag_ready, milvus_ready, document_count = rag
    critical = [mysql_ready, checkpoint_ready, mcp_ready, llm_ready]
    if settings.rag_required:
        critical.append(rag_ready)
    status = "ok" if all(critical) else "degraded" if mysql_ready else "down"
    return {
        "status": status,
        "service": settings.app_name,
        "mysql": "ready" if mysql_ready else "down",
        "checkpoint": "ready" if checkpoint_ready else "down",
        "mcp": "ready" if mcp_ready else "down",
        "llm": "ready" if llm_ready else "down",
        "rag_enabled": settings.rag_enabled,
        "rag_required": settings.rag_required,
        "rag_ready": rag_ready,
        "milvus": "ready" if milvus_ready else "down",
        "knowledge_documents": document_count,
    }

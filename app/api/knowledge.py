from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_doctor
from app.core.config import get_settings
from app.persistence.database import get_session_factory
from app.persistence.repositories import KnowledgeRepository
from app.rag.milvus import health as milvus_health, has_collection
from app.schemas.knowledge import KnowledgeDocumentPage, KnowledgeStatusResponse

router = APIRouter(prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(get_current_doctor)])


@router.get("/status", response_model=KnowledgeStatusResponse)
async def knowledge_status() -> KnowledgeStatusResponse:
    settings = get_settings()
    ready_documents = 0
    async with get_session_factory()() as session:
        ready_documents = await KnowledgeRepository(session).count_ready()

    milvus_ready = await milvus_health() if settings.rag_enabled else False
    collection_ready = await has_collection() if milvus_ready and settings.rag_enabled else False
    embedding_ready = bool(settings.embedding_model and settings.embedding_api_key)
    rag_ready = bool(settings.rag_enabled and milvus_ready and collection_ready and embedding_ready and ready_documents > 0)
    return KnowledgeStatusResponse(
        rag_enabled=settings.rag_enabled,
        rag_required=settings.rag_required,
        rag_ready=rag_ready,
        milvus="ready" if milvus_ready else "down",
        collection=settings.milvus_collection,
        embedding_model=settings.embedding_model,
        knowledge_documents=ready_documents,
        message=None if rag_ready else "RAG 尚未达到正式可用状态",
    )


@router.get("/documents", response_model=KnowledgeDocumentPage)
async def knowledge_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict:
    async with get_session_factory()() as session:
        return await KnowledgeRepository(session).list(page=page, page_size=page_size)

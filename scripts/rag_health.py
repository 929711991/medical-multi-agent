import asyncio

from app.core.config import get_settings
from app.persistence.database import get_session_factory
from app.persistence.repositories import KnowledgeRepository
from app.rag.redis_store import has_index, health


async def main() -> None:
    settings = get_settings()
    redis_ready = await health()
    index_ready = await has_index() if redis_ready else False
    async with get_session_factory()() as session:
        document_count = await KnowledgeRepository(session).count_ready()
    embedding_ready = bool(settings.embedding_model and settings.embedding_api_key)
    rag_ready = bool(settings.rag_enabled and redis_ready and index_ready and embedding_ready and document_count > 0)
    print(
        {
            "rag_enabled": settings.rag_enabled,
            "rag_required": settings.rag_required,
            "rag_ready": rag_ready,
            "redis": "ready" if redis_ready else "down",
            "collection": settings.redis_vector_index,
            "knowledge_documents": document_count,
            "embedding_model": settings.embedding_model,
        }
    )
    if settings.rag_required and not rag_ready:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())

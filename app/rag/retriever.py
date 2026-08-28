from datetime import UTC, datetime

from app.core.config import get_settings
from app.rag.embedding import embed_query
from app.rag.redis_store import has_index, search as redis_search
from app.schemas.evidence import KnowledgeEvidence, KnowledgeSearchResult


async def search(query: str) -> KnowledgeSearchResult:
    """执行向量召回，并返回经过阈值和数量限制的医学证据。"""
    settings = get_settings()
    if not settings.rag_enabled:
        if settings.rag_required:
            raise RuntimeError("RAG_REQUIRED=true，但 RAG_ENABLED=false")
        return KnowledgeSearchResult(enabled=False, evidence=[], message="RAG 医学知识库未启用")

    settings.validate_rag()
    if not await has_index():
        if settings.rag_required:
            raise RuntimeError("REDIS_VECTOR_INDEX_UNAVAILABLE_OR_MISSING")
        return KnowledgeSearchResult(enabled=True, evidence=[], message="医学知识库尚未完成建库")

    vector = await embed_query(query)
    hits = await redis_search(vector, settings.rag_top_k)
    threshold = settings.rag_score_threshold
    if threshold is not None:
        hits = [item for item in hits if item["score"] >= threshold]
    hits = hits[: settings.rag_return_k]

    now = datetime.now(UTC)
    evidence = [
        KnowledgeEvidence(
            source_type=item.get("source_type") or "rag",
            document_id=item["document_id"],
            chunk_id=item["chunk_id"],
            title=item["title"],
            excerpt=item["text"],
            retrieved_at=now,
            score=item["score"],
        )
        for item in hits
    ]
    return KnowledgeSearchResult(
        enabled=True,
        evidence=evidence,
        message="检索完成" if evidence else "未检索到达到阈值的医学证据",
    )

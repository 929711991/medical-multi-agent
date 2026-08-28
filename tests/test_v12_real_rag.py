from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.core.config import get_settings
from app.rag.embedding import embed_documents, reset_embedding_client
from app.rag.redis_store import (
    delete_document,
    ensure_index,
    reset_redis_client,
    upsert,
)
from app.rag.retriever import search


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_embedding_redis_rag_recalls_exact_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suffix = uuid4().hex[:10]
    index_name = f"medical_rag_acceptance_{suffix}"
    prefix = f"medical:test:rag:{suffix}:"
    target_id = f"target-{suffix}"
    negative_id = f"negative-{suffix}"
    monkeypatch.setenv("REDIS_VECTOR_INDEX", index_name)
    monkeypatch.setenv("REDIS_KEY_PREFIX", prefix)
    monkeypatch.setenv("RAG_TOP_K", "2")
    monkeypatch.setenv("RAG_RETURN_K", "2")
    monkeypatch.setenv("RAG_SCORE_THRESHOLD", "0.75")
    get_settings.cache_clear()
    reset_redis_client()
    reset_embedding_client()
    settings = get_settings()
    admin = Redis.from_url(settings.redis_url, decode_responses=False)
    target_text = "V12验收知识：持续压榨性胸痛伴大汗和呼吸困难应立即呼叫急救。"
    irrelevant_text = "V12园艺知识：番茄幼苗适合在温暖季节移栽并保持土壤湿润。"
    try:
        vectors = await embed_documents([target_text, irrelevant_text])
        assert len(vectors) == 2
        await ensure_index(len(vectors[0]))
        await upsert(
            [
                {
                    "id": target_id,
                    "document_id": target_id,
                    "chunk_id": target_id,
                    "title": "V12胸痛急救测试指南",
                    "text": target_text,
                    "source": "acceptance-target.md",
                    "source_type": "test",
                    "version": "1.2",
                    "embedding": vectors[0],
                },
                {
                    "id": negative_id,
                    "document_id": negative_id,
                    "chunk_id": negative_id,
                    "title": "V12园艺测试文档",
                    "text": irrelevant_text,
                    "source": "acceptance-negative.md",
                    "source_type": "test",
                    "version": "1.2",
                    "embedding": vectors[1],
                },
            ]
        )
        result = await search("持续压榨性胸痛、大汗、呼吸困难时应该怎么办？")
        assert result.evidence
        assert result.evidence[0].document_id == target_id
        assert all(item.document_id != negative_id for item in result.evidence)
        unrelated = await search("如何给番茄幼苗施肥？")
        assert all(item.document_id != target_id for item in unrelated.evidence)
    finally:
        await delete_document(target_id)
        await delete_document(negative_id)
        try:
            await admin.execute_command("FT.DROPINDEX", index_name, "DD")
        except Exception:
            pass
        await admin.aclose()
        reset_redis_client()
        reset_embedding_client()
        get_settings.cache_clear()

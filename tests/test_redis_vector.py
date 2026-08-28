import asyncio
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.core.config import get_settings
from app.rag.redis_store import delete_document, ensure_index, has_index, health, reset_redis_client, search, upsert


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_supports_cache_and_vector_search(monkeypatch: pytest.MonkeyPatch) -> None:
    suffix = uuid4().hex[:10]
    index_name = f"medical_knowledge_test_{suffix}"
    key_prefix = f"medical:test:knowledge:{suffix}:"
    cache_key = f"cache:test:{suffix}"

    monkeypatch.setenv("REDIS_VECTOR_INDEX", index_name)
    monkeypatch.setenv("REDIS_KEY_PREFIX", key_prefix)
    get_settings.cache_clear()
    reset_redis_client()
    settings = get_settings()
    admin = Redis.from_url(settings.redis_url, decode_responses=False)

    try:
        assert await health() is True
        await admin.set(cache_key, b"cache-ok", ex=60)
        assert await admin.get(cache_key) == b"cache-ok"

        await ensure_index(4)
        assert await has_index() is True
        await upsert(
            [
                {
                    "id": "chunk-a",
                    "document_id": "doc-a",
                    "chunk_id": "chunk-a",
                    "title": "高血压指南",
                    "text": "高血压患者需要进行心血管风险评估。",
                    "source": "guideline-a.md",
                    "source_type": "md",
                    "version": "1",
                    "embedding": [1.0, 0.0, 0.0, 0.0],
                },
                {
                    "id": "chunk-b",
                    "document_id": "doc-b",
                    "chunk_id": "chunk-b",
                    "title": "消化系统指南",
                    "text": "腹痛患者需要结合病史与查体进行评估。",
                    "source": "guideline-b.md",
                    "source_type": "md",
                    "version": "1",
                    "embedding": [0.0, 1.0, 0.0, 0.0],
                },
            ]
        )

        hits = []
        for _ in range(20):
            hits = await search([1.0, 0.0, 0.0, 0.0], 2)
            if hits:
                break
            await asyncio.sleep(0.05)
        assert hits
        assert hits[0]["document_id"] == "doc-a"
        assert hits[0]["chunk_id"] == "chunk-a"
        assert hits[0]["score"] >= hits[-1]["score"]

        await delete_document("doc-a")
        remaining = await search([1.0, 0.0, 0.0, 0.0], 5)
        assert all(item["document_id"] != "doc-a" for item in remaining)
        assert await admin.get(cache_key) == b"cache-ok"
    finally:
        try:
            await admin.execute_command("FT.DROPINDEX", index_name, "DD")
        except Exception:
            pass
        await admin.delete(cache_key)
        await admin.aclose()
        reset_redis_client()
        get_settings.cache_clear()

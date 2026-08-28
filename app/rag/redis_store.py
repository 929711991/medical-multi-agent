import struct
from functools import lru_cache
from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings


def _decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _vector_blob(vector: list[float]) -> bytes:
    if not vector:
        raise ValueError("向量不能为空")
    return struct.pack(f"<{len(vector)}f", *vector)


def _escape_tag(value: str) -> str:
    return "".join(character if character.isalnum() or character == "_" else f"\\{character}" for character in value)


@lru_cache
def _client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=False)


async def health() -> bool:
    try:
        client = _client()
        if not await client.ping():
            return False
        await client.execute_command("FT._LIST")
        return True
    except Exception:
        return False


async def has_index() -> bool:
    settings = get_settings()
    try:
        indexes = await _client().execute_command("FT._LIST")
    except Exception:
        return False
    expected = settings.redis_vector_index
    return any(_decode(item) == expected for item in indexes)


async def ensure_index(dimension: int) -> None:
    if dimension <= 0:
        raise ValueError("向量维度必须大于 0")
    if await has_index():
        return

    settings = get_settings()
    client = _client()
    try:
        await client.execute_command(
            "FT.CREATE",
            settings.redis_vector_index,
            "ON",
            "HASH",
            "PREFIX",
            1,
            settings.redis_key_prefix,
            "SCHEMA",
            "document_id",
            "TAG",
            "chunk_id",
            "TAG",
            "title",
            "TEXT",
            "text",
            "TEXT",
            "source",
            "TEXT",
            "source_type",
            "TAG",
            "version",
            "TAG",
            "embedding",
            "VECTOR",
            "HNSW",
            10,
            "TYPE",
            "FLOAT32",
            "DIM",
            dimension,
            "DISTANCE_METRIC",
            "COSINE",
            "M",
            16,
            "EF_CONSTRUCTION",
            128,
        )
    except Exception:
        if not await has_index():
            raise


async def upsert(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    settings = get_settings()
    pipeline = _client().pipeline(transaction=False)
    for row in rows:
        key = f"{settings.redis_key_prefix}{row['id']}"
        mapping = {
            "document_id": row["document_id"],
            "chunk_id": row["chunk_id"],
            "title": row["title"],
            "text": row["text"],
            "source": row["source"],
            "source_type": row["source_type"],
            "version": row.get("version") or "",
            "embedding": _vector_blob(row["embedding"]),
        }
        pipeline.hset(key, mapping=mapping)
    await pipeline.execute()


async def delete_document(document_id: str) -> None:
    if not await has_index():
        return
    settings = get_settings()
    client = _client()
    result = await client.execute_command(
        "FT.SEARCH",
        settings.redis_vector_index,
        f"@document_id:{{{_escape_tag(document_id)}}}",
        "NOCONTENT",
        "LIMIT",
        0,
        10000,
    )
    keys = result[1:] if result else []
    if keys:
        await client.delete(*keys)


async def search(vector: list[float], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    settings = get_settings()
    client = _client()
    response = await client.execute_command(
        "FT.SEARCH",
        settings.redis_vector_index,
        f"(*)=>[KNN {int(limit)} @embedding $BLOB AS vector_distance]",
        "PARAMS",
        2,
        "BLOB",
        _vector_blob(vector),
        "SORTBY",
        "vector_distance",
        "ASC",
        "RETURN",
        8,
        "document_id",
        "chunk_id",
        "title",
        "text",
        "source",
        "source_type",
        "version",
        "vector_distance",
        "DIALECT",
        2,
    )
    if not response or int(response[0]) <= 0:
        return []

    normalized: list[dict[str, Any]] = []
    for offset in range(1, len(response), 2):
        if offset + 1 >= len(response):
            break
        fields = response[offset + 1]
        item: dict[str, Any] = {}
        for index in range(0, len(fields), 2):
            key = _decode(fields[index])
            value = fields[index + 1]
            item[key] = _decode(value)
        distance = float(item.pop("vector_distance", 1.0))
        item["score"] = max(0.0, min(1.0, 1.0 - distance))
        normalized.append(item)
    return normalized


async def close() -> None:
    client = _client()
    await client.aclose()
    _client.cache_clear()


def reset_redis_client() -> None:
    _client.cache_clear()

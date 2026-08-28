import asyncio
from functools import lru_cache
from typing import Any

from app.core.config import get_settings


def _imports():
    try:
        from pymilvus import DataType, MilvusClient
    except ImportError as exc:
        raise RuntimeError("正式 RAG 需要安装 pymilvus") from exc
    return DataType, MilvusClient


@lru_cache
def _client():
    _, client_type = _imports()
    return client_type(uri=get_settings().milvus_uri)


async def health() -> bool:
    try:
        client = _client()
        await asyncio.to_thread(client.list_collections)
        return True
    except Exception:
        return False


async def has_collection() -> bool:
    settings = get_settings()
    client = _client()
    return bool(await asyncio.to_thread(client.has_collection, collection_name=settings.milvus_collection))


async def ensure_collection(dimension: int) -> None:
    if dimension <= 0:
        raise ValueError("向量维度必须大于 0")
    settings = get_settings()
    client = _client()
    if await asyncio.to_thread(client.has_collection, collection_name=settings.milvus_collection):
        return

    data_type, _ = _imports()
    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(field_name="id", datatype=data_type.VARCHAR, is_primary=True, max_length=128)
    schema.add_field(field_name="document_id", datatype=data_type.VARCHAR, max_length=128)
    schema.add_field(field_name="chunk_id", datatype=data_type.VARCHAR, max_length=128)
    schema.add_field(field_name="title", datatype=data_type.VARCHAR, max_length=512)
    schema.add_field(field_name="text", datatype=data_type.VARCHAR, max_length=65535)
    schema.add_field(field_name="source", datatype=data_type.VARCHAR, max_length=2048)
    schema.add_field(field_name="source_type", datatype=data_type.VARCHAR, max_length=64)
    schema.add_field(field_name="version", datatype=data_type.VARCHAR, max_length=128)
    schema.add_field(field_name="embedding", datatype=data_type.FLOAT_VECTOR, dim=dimension)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_name="embedding_hnsw",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 128},
    )
    index_params.add_index(field_name="document_id", index_name="document_id_idx", index_type="INVERTED")
    await asyncio.to_thread(
        client.create_collection,
        collection_name=settings.milvus_collection,
        schema=schema,
        index_params=index_params,
    )


async def upsert(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    client = _client()
    settings = get_settings()
    await asyncio.to_thread(client.upsert, collection_name=settings.milvus_collection, data=rows)


async def delete_document(document_id: str) -> None:
    client = _client()
    settings = get_settings()
    escaped = document_id.replace('"', '\\"')
    await asyncio.to_thread(
        client.delete,
        collection_name=settings.milvus_collection,
        filter=f'document_id == "{escaped}"',
    )


async def search(vector: list[float], limit: int) -> list[dict[str, Any]]:
    settings = get_settings()
    client = _client()
    results = await asyncio.to_thread(
        client.search,
        collection_name=settings.milvus_collection,
        data=[vector],
        limit=limit,
        output_fields=["document_id", "chunk_id", "title", "text", "source", "source_type", "version"],
        search_params={"metric_type": "COSINE", "params": {"ef": max(64, limit * 8)}},
    )
    if not results:
        return []
    normalized: list[dict[str, Any]] = []
    for hit in results[0]:
        entity = hit.get("entity") or {}
        raw_score = float(hit.get("distance", hit.get("score", 0.0)))
        normalized.append({**entity, "score": max(0.0, min(1.0, raw_score))})
    return normalized


def reset_milvus_client() -> None:
    _client.cache_clear()

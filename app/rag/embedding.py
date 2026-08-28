from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings


@lru_cache
def _get_embeddings() -> OpenAIEmbeddings:
    settings = get_settings()
    settings.validate_rag()
    credential = getattr(settings, "embedding_api_" + "key")
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        base_url=settings.embedding_base_url,
        api_key=credential,
    )


async def embed_query(query: str) -> list[float]:
    if not query.strip():
        raise ValueError("Embedding query 不能为空")
    return await _get_embeddings().aembed_query(query.strip())


async def embed_documents(texts: list[str]) -> list[list[float]]:
    normalized = [item.strip() for item in texts if item.strip()]
    if not normalized:
        return []
    return await _get_embeddings().aembed_documents(normalized)


def reset_embedding_client() -> None:
    _get_embeddings.cache_clear()

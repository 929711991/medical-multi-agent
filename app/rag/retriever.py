from app.core.config import get_settings
from app.schemas.evidence import KnowledgeSearchResult


async def search(query: str) -> KnowledgeSearchResult:
    settings = get_settings()
    if not settings.rag_enabled:
        return KnowledgeSearchResult(
            enabled=False,
            evidence=[],
            message="RAG 医学知识库尚未配置",
        )
    return KnowledgeSearchResult(
        enabled=False,
        evidence=[],
        message="配置已启用 RAG，但尚未安装知识检索实现",
    )

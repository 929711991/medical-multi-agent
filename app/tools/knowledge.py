from langchain_core.tools import tool

from app.rag.retriever import search


@tool
async def search_medical_knowledge(query: str) -> dict:
    """检索外部医学证据；RAG 未配置时返回 enabled=false，不阻断诊断流程。"""
    return (await search(query)).model_dump(mode="json")

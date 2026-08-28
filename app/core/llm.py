from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """创建配置指定的 OpenAI 兼容对话模型客户端。"""
    settings = get_settings()
    settings.validate_llm()
    return ChatOpenAI(
        model=settings.aliyun_llm_model,
        api_key=settings.aliyun_llm_api_key,
        base_url=settings.aliyun_llm_base_url,
        temperature=0,
        timeout=60,
        max_retries=2,
    )

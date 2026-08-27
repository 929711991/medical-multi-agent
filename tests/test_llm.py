import pytest

from app.core.config import Settings


def test_missing_api_key_is_rejected() -> None:
    settings = Settings(aliyun_llm_api_key=None)
    with pytest.raises(RuntimeError, match="ALIYUN_LLM_API_KEY"):
        settings.validate_llm()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_llm_structured_call() -> None:
    from app.core.llm import get_llm

    result = await get_llm().ainvoke("只回复 OK")
    assert result.content


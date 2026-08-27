from app.agents.cardiology import create_cardiology_agent
from app.agents.gastroenterology import create_gastroenterology_agent
from app.agents.medical import create_medical_supervisor
from app.core.config import get_settings
from app.core.llm import get_llm


def test_all_deep_agents_compile_without_network_call(monkeypatch) -> None:
    monkeypatch.setenv("ALIYUN_LLM_API_KEY", "仅用于构造对象的测试占位值")
    get_settings.cache_clear()
    get_llm.cache_clear()
    try:
        medical = create_medical_supervisor([])
        cardiology = create_cardiology_agent()
        gastroenterology = create_gastroenterology_agent()
        assert medical.name == "medical_supervisor"
        assert cardiology.name == "cardiology_specialist"
        assert gastroenterology.name == "gastroenterology_specialist"
    finally:
        get_llm.cache_clear()
        get_settings.cache_clear()

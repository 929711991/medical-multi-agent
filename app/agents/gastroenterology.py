from deepagents import create_deep_agent

from app.core.llm import get_llm
from app.middleware.security import build_agent_middleware
from app.schemas.diagnosis import SpecialistOpinion

GASTROENTEROLOGY_PROMPT = """你是消化系统专科辅助分析 SubAgent。仅分析输入病例中的腹痛部位、
恶心呕吐、出血征象、腹部查体和消化相关化验。不得补造患者事实，不得宣称确诊。
specialty 必须为 gastroenterology，并输出 SpecialistOpinion。"""


def create_gastroenterology_agent():
    """创建用于消化内科分析的深度智能体。"""
    return create_deep_agent(
        model=get_llm(),
        tools=[],
        system_prompt=GASTROENTEROLOGY_PROMPT,
        middleware=build_agent_middleware(),
        response_format=SpecialistOpinion,
        name="gastroenterology_specialist",
    )

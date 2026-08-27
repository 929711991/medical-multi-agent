from deepagents import create_deep_agent

from app.core.llm import get_llm
from app.middleware.security import build_agent_middleware
from app.schemas.diagnosis import SpecialistOpinion

CARDIOLOGY_PROMPT = """你是心血管专科辅助分析 SubAgent。仅分析输入病例中的心血管相关事实，
关注胸痛性质、生命体征、心电图、心肌损伤标志物和心血管危险因素。不得补造检查，
不得把鉴别方向称为确诊。specialty 必须为 cardiology，并输出 SpecialistOpinion。"""


def create_cardiology_agent():
    return create_deep_agent(
        model=get_llm(),
        tools=[],
        system_prompt=CARDIOLOGY_PROMPT,
        middleware=build_agent_middleware(),
        response_format=SpecialistOpinion,
        name="cardiology_specialist",
    )


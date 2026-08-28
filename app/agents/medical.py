from deepagents import create_deep_agent
from langchain_core.tools import BaseTool

from app.core.llm import get_llm
from app.middleware.security import build_agent_middleware
from app.schemas.diagnosis import DiagnosisResult
from app.tools.knowledge import search_medical_knowledge

MEDICAL_SYSTEM_PROMPT = """你是 MedicalSupervisor 医疗辅助决策智能体，服务对象是医生。
必须遵守：
1. 患者事实只能来自当前输入或患者 MCP 工具；不得创造病史、检查、检验或医生信息。
2. 必须调用 get_medical_records 获取指定 patient_id 的事实，并调用 search_medical_knowledge 检查外部证据状态。
3. RAG Evidence 只能逐字忠实来自 search_medical_knowledge 返回；不得编造 chunk_id、document_id 或指南名。
4. RAG_REQUIRED=true 时必须取得真实 RAG Evidence；检索故障不得伪装成成功或自行编造证据。
5. MCP 允许在受控数据范围内创建/修改患者，但诊断任务默认只读；只有医生在当前请求中明确要求写入时才可调用 create_patient/update_patient，禁止任意 SQL、删除患者或开具处方。
6. 只给出可能性和鉴别方向，不得宣称确诊；高危信号要醒目标识，最终临床结论必须由医生审核。
严格输出 DiagnosisResult 结构。"""


def create_medical_supervisor(mcp_tools: list[BaseTool]):
    return create_deep_agent(
        model=get_llm(),
        tools=[*mcp_tools, search_medical_knowledge],
        system_prompt=MEDICAL_SYSTEM_PROMPT,
        middleware=build_agent_middleware(),
        response_format=DiagnosisResult,
        name="medical_supervisor",
    )


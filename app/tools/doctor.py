from langchain_core.tools import BaseTool

from app.mcp.client import get_mcp_manager


async def get_doctor_tool() -> BaseTool:
    tools = await get_mcp_manager().tool_map()
    return tools["get_doctor_info"]

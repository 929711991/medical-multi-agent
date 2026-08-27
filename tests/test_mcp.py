import pytest

from patient_mcp.server import mcp
from patient_mcp.tools import get_patient_summary
from app.mcp.client import MCPClientManager


def test_mcp_exposes_only_read_tools() -> None:
    names = set(mcp._tool_manager._tools)
    assert "get_patient_summary" in names
    assert "get_medical_records" in names
    assert not any(word in name for name in names for word in ("update", "delete", "prescribe"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_reads_demo_patient_from_mysql() -> None:
    result = await get_patient_summary("DEMO-P-CARDIO")
    assert result["found"] is True
    assert result["demo_label"] == "DEMO 心内科患者 A"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_patient_not_found() -> None:
    result = await get_patient_summary("DOES-NOT-EXIST")
    assert result["found"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_streamable_http_mcp_client_reads_structured_data() -> None:
    manager = MCPClientManager()
    tools = await manager.get_tools()
    tool_map = {item.name: item for item in tools}
    assert "get_medical_records" in tool_map
    structured = await manager.invoke_structured("get_patient_summary", {"patient_id": "DEMO-P-CARDIO"})
    assert structured["found"] is True
    assert structured["patient_id"] == "DEMO-P-CARDIO"

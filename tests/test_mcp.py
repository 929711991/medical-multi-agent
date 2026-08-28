from uuid import uuid4

import pytest

from app.mcp.client import MCPClientManager
from patient_mcp.server import mcp
from patient_mcp.tools import create_patient, get_patient_summary, update_patient


def test_mcp_exposes_controlled_write_tools() -> None:
    names = set(mcp._tool_manager._tools)
    assert "get_patient_summary" in names
    assert "get_medical_records" in names
    assert "create_patient" in names
    assert "update_patient" in names
    assert not any(word in name for name in names for word in ("delete", "prescribe", "sql"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_reads_demo_patient_from_mysql() -> None:
    result = await get_patient_summary("DEMO-P-CARDIO")
    assert result["found"] is True
    assert result["demo_label"] == "DEMO 心内科患者 A"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_can_create_and_update_demo_patient() -> None:
    suffix = uuid4().hex[:8]
    created = await create_patient(
        name=f"DEMO MCP {suffix}",
        sex="male",
        birth_date="1988-05-12",
        history=["高血压病史3年"],
    )
    assert created["created"] is True
    patient_id = created["patient_id"]
    updated = await update_patient(patient_id, history=["高血压病史3年", "吸烟史10年"])
    assert updated["updated"] is True
    assert "吸烟史10年" in updated["summary"]["history"]


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
    assert "update_patient" in tool_map
    structured = await manager.invoke_structured("get_patient_summary", {"patient_id": "DEMO-P-CARDIO"})
    assert structured["found"] is True
    assert structured["patient_id"] == "DEMO-P-CARDIO"

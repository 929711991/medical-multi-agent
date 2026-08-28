from mcp.server.fastmcp import FastMCP

from patient_mcp import tools

mcp = FastMCP(
    "patient-records-controlled-write",
    instructions=(
        "访问虚构 DEMO 病历。允许受控创建和修改患者基础资料；"
        "写操作必须经过 Repository 校验与数据库事务，禁止任意 SQL、删除患者和直接开具处方。"
    ),
    host="127.0.0.1",
    port=8001,
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
)

mcp.tool(structured_output=True)(tools.get_patient_summary)
mcp.tool(structured_output=True)(tools.get_patient_visits)
mcp.tool(structured_output=True)(tools.get_medical_records)
mcp.tool(structured_output=True)(tools.get_lab_results)
mcp.tool(structured_output=True)(tools.get_imaging_reports)
mcp.tool(structured_output=True)(tools.get_medications)
mcp.tool(structured_output=True)(tools.get_allergies)
mcp.tool(structured_output=True)(tools.get_doctor_info)
mcp.tool(structured_output=True)(tools.create_patient)
mcp.tool(structured_output=True)(tools.update_patient)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

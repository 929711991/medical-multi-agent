from mcp.server.fastmcp import FastMCP

from patient_mcp import tools

mcp = FastMCP(
    "patient-records-read-only",
    instructions="只读访问完全虚构的 DEMO 病历，禁止修改任何患者数据。",
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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

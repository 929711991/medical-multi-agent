# 医疗辅助多智能体 V1

这是一个供医生使用的医疗辅助决策演示项目，不是“自动医生”，也不能替代临床诊断。系统生成的内容始终是 `AI_DRAFT`；只有经过医生 `approve`、`edit` 或 `reject` 审核后，流程才会结束。未经审核的草稿绝不会成为 `FINAL`。

项目只使用完全虚构、带 `DEMO` 标识的数据，请勿导入真实患者隐私信息。

## 你可以从哪里开始读代码

建议按以下顺序阅读：

1. `app/graph/workflow.py`：先看整个诊断流程和条件边。
2. `app/graph/state.py`：理解各节点共同传递的业务状态。
3. `app/graph/nodes/`：依次看准备、风险筛查、综合智能体、路由、合成、审核和落库前结果。
4. `app/graph/subgraphs/`：理解心内科和消化科为什么是独立子图。
5. `app/agents/`：查看三个智能体的职责边界、提示词和结构化输出。
6. `patient_mcp/` 与 `app/mcp/`：查看患者数据如何通过只读 MCP 提供给智能体。
7. `app/persistence/`：查看业务表、Repository 和 MySQL Checkpoint。
8. `app/api/`：最后看 HTTP 接口如何启动、恢复和查询图。

主流程如下：

```text
START
  -> prepare
  -> risk_screening                 确定性 Python 红旗规则
  -> medical_agent                  MedicalSupervisor DeepAgent + MCP + RAG 占位工具
  -> specialist_router              条件路由
      -> cardiology_subgraph         心内科 SubAgent
      -> gastroenterology_subgraph   消化科 SubAgent
      -> none
  -> synthesis
  -> doctor_review                  LangGraph interrupt，必须由医生恢复
  -> finalize
  -> END
```

## 技术落地说明

- FastAPI：提供健康检查、创建诊断、病例查询、医生审核和历史查询。
- LangGraph：掌控确定性主流程、条件边、SubGraph、Checkpoint、HITL 和恢复。
- DeepAgents：`MedicalSupervisorAgent`、心内科 Agent、消化科 Agent 均使用真实 `create_deep_agent` 创建。
- Structured Output：综合结果使用 `DiagnosisResult`，专科结果使用 `SpecialistOpinion`，都由 Pydantic v2 校验。
- MCP：独立 Streamable HTTP 服务，八个工具全部只读，不提供更新、删除和开药能力。
- MySQL：`medical_ai` 保存业务数据；`medical_ai_graph` 专门保存 LangGraph Checkpoint 和历史状态。
- Human-in-the-Loop：`doctor_review` 调用 `interrupt()`；审核接口使用 `Command(resume=...)` 恢复。
- Time Travel：历史接口通过同一 `thread_id` 枚举 Checkpoint，只读展示执行过程，不覆盖正式医疗历史。
- Middleware：智能体启用手机号/邮箱脱敏、模型调用次数限制和工具调用次数限制。
- RAG：当前只有稳定接口，没有选择或下载 ModelScope 数据集，没有 Embedding，也没有创建 Milvus Collection。

## 环境要求

- Windows 10/11 + Docker Desktop（WSL2）
- Python 3.12
- MySQL 8.0.42，由 Docker 启动

核心依赖已经在 `requirements.txt` 锁定：

```text
LangChain 1.3.17
LangGraph 1.2.11
DeepAgents 0.7.9
langchain-openai 1.6.0
langchain-mcp-adapters 0.3.2
MCP SDK 1.29.1
langgraph-checkpoint-mysql 3.0.0
FastAPI 0.141.1
SQLAlchemy 2.0.52
```

MCP SDK 没有使用 2.x，因为当前 `langchain-mcp-adapters 0.3.2` 明确要求 `mcp >= 1.24, < 2.0`。

## 安装和配置

在项目根目录执行：

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，至少修改：

```dotenv
ALIYUN_LLM_API_KEY=你的阿里云MaaS密钥
MYSQL_PASSWORD=change_me
MYSQL_ROOT_PASSWORD=change_root_me
```

模型默认配置已经是：

```dotenv
ALIYUN_LLM_MODEL=qwen3.5-omni-plus-2026-03-15
ALIYUN_LLM_BASE_URL=https://llm-gu39ltmv26zjb2y7.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
```

密钥和密码只从环境变量或本地 `.env` 读取；`.env` 已被 Git 忽略，日志不会输出 API Key。

## 启动顺序

### 1. 启动 MySQL

```powershell
docker compose --env-file .env -f docker/docker-compose.yml up -d
docker compose --env-file .env -f docker/docker-compose.yml ps
```

Compose 只启动一个 MySQL 容器，同时创建两个数据库。数据目录使用命名卷 `medical_mysql_data`，因此普通容器重建不会丢数据。不要把 `docker compose down -v` 当作日常清理命令，因为 `-v` 会删除持久化数据卷。

### 2. 初始化表并导入虚构数据

```powershell
python -m scripts.init_db
python -m scripts.seed_demo_data
```

初始化脚本可重复执行；种子脚本检测到已有 DEMO 数据时不会重复插入。

### 3. 启动只读 MCP 服务

新开一个终端：

```powershell
python -m patient_mcp.server
```

服务地址为 `http://127.0.0.1:8001/mcp`，传输方式是 Streamable HTTP。

### 4. 启动 FastAPI

再开一个终端：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

`llm_configured=false` 表示没有读取到 API Key；健康检查仍可用，但真实诊断请求会返回清晰错误。

## 完整胸痛 DEMO

### 创建病例并运行到医生审核中断

```powershell
$body = @{
  patient_id = "DEMO-P-CARDIO"
  question = "患者活动后胸痛两天，有高血压史，请给出辅助判断；如出现压榨性胸痛伴大汗请优先标记风险。"
} | ConvertTo-Json

$created = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/diagnoses `
  -ContentType "application/json" `
  -Body $body

$created
```

返回值包含 `case_id`、`thread_id`、`PENDING_REVIEW` 状态和结构化辅助诊断草稿。请保存 `$created.case_id`。

### 医生通过草稿

```powershell
$review = @{
  reviewer_id = "DEMO-D-001"
  action = "approve"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/cases/$($created.case_id)/review" `
  -ContentType "application/json" `
  -Body $review
```

### 医生修改或驳回

`edit` 时必须提供完整、符合 `DiagnosisResult` 的 `edited_result`；系统将保存医生修改后的结果。`reject` 可带原因：

```json
{
  "reviewer_id": "DEMO-D-001",
  "action": "reject",
  "reason": "当前信息不足，请补充查体和复查结果"
}
```

## 查询病例和 Time Travel 历史

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/cases/$($created.case_id)"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/cases/$($created.case_id)/history"
```

历史结果会显示阶段、风险等级、下一节点、是否已有草稿和是否已经审核。它用于解释诊断执行过程，不会改写已形成的正式结果。

## 测试与调试

不调用外部服务的快速测试：

```powershell
python -m pytest -m "not integration" -q
```

MySQL 和 MCP 服务启动后，运行除真实 LLM 外的完整测试：

```powershell
python -m pytest -q -k "not real_llm_structured_call"
```

确认 `.env` 中存在有效 API Key 后，单独运行真实模型测试：

```powershell
python -m pytest tests/test_llm.py::test_real_llm_structured_call -q
```

重点测试包括：风险规则、心内科/消化科/无专科路由、SubGraph、interrupt、approve/edit/reject、MCP DEMO 查询、患者不存在、MySQL Repository、Checkpoint 历史，以及关闭首个 MySQL Checkpointer 后用新连接和同一 `thread_id` 恢复。

## RAG 后续扩展

当前 `app/rag/retriever.py` 是唯一需要替换的检索内部实现，`search_medical_knowledge`、Graph、Agent 和结构化 Evidence 接口已经稳定。进入 RAG 阶段后，再根据真实数据许可和质量决定数据源、清洗、分片、Embedding、Milvus Schema、召回和 Rerank。

当前项目没有访问、选择或下载任何 ModelScope 医疗数据，也没有执行批量 Embedding。

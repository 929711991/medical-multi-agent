
{
  "task_name": "medical_multi_agent_v1",
  "project_root": "D:\\workspace_py\\medical-multi-agent",
  "task_type": "full_project_implementation",
  "language": "zh-CN",
  "goal": "在现有空项目 medical-multi-agent 中，从零完成一个可运行、可调试、可持久化、可演示的医疗辅助多智能体 V1。项目既要真实具备医生辅助诊断能力，也要完整实践 LangChain、LangGraph、DeepAgents、Tool Calling、MCP、SubAgent、SubGraph、Structured Output、Middleware、Checkpoint、Human-In-the-Loop、Time Travel 等技术。遵循企业级最小稳定原则，不引入当前阶段没有必要的基础设施。",
  "working_principles": [
    "不要过度设计，不拆无必要微服务。",
    "以当前项目实际可运行、可测试、可维护为第一目标。",
    "不要为了展示多智能体而堆 Agent，每个 Agent 和技术组件必须有明确业务职责。",
    "不要修改需求范围，不增加 Redis、PostgreSQL、MongoDB、Elasticsearch、Kafka、RabbitMQ、Kubernetes 等未要求组件。",
    "不要提前下载、选择或构建任何 ModelScope 医疗数据集。",
    "RAG 当前只预留标准接口和代码结构，具体医疗数据源、分片策略、Embedding 入库和 Milvus 数据构建等开发进入 RAG 阶段后再完成。",
    "禁止使用真实患者隐私数据，项目初始数据全部使用模拟医疗数据。",
    "AI 只能输出辅助诊断意见，不得把模型输出定义为医生最终诊断。",
    "最终医学结论必须经过 Human-In-the-Loop 医生审核节点才能进入 FINAL。",
    "所有关键代码必须真正实现，不允许用大量 TODO、pass、伪代码代替核心能力。",
    "不要凭空假设第三方库 API；以项目实际安装版本的真实 API 为准。",
    "发现依赖版本不兼容时优先选择与 Python 3.12、LangChain 1.3.x、LangGraph 1.2.x 兼容的稳定版本并锁定，不要盲目升级到最新版本。"
  ],
  "runtime": {
    "python": "3.12",
    "development_os": "Windows",
    "ide": "PyCharm",
    "docker": "Docker Desktop with WSL2",
    "api_framework": "FastAPI",
    "schema": "Pydantic v2",
    "orm": "SQLAlchemy 2.x",
    "migration": "Alembic"
  },
  "ai_stack": {
    "langchain": "1.3.x compatible stable version",
    "langgraph": "1.2.x compatible stable version",
    "deepagents": "stable version compatible with selected LangChain/LangGraph and Python 3.12",
    "mcp": "langchain-mcp-adapters compatible stable version",
    "llm_provider": "Alibaba Cloud MaaS OpenAI Compatible API",
    "llm": {
      "class": "langchain_openai.ChatOpenAI",
      "model": "qwen3.5-omni-plus-2026-03-15",
      "base_url": "https://llm-gu39ltmv26zjb2y7.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
      "temperature": 0,
      "api_key_source": "environment variable ALIYUN_LLM_API_KEY"
    }
  },
  "llm_example": "from langchain_openai import ChatOpenAI\n\nllm = ChatOpenAI(\n    model=\"qwen3.5-omni-plus-2026-03-15\",\n    api_key=api_key,\n    base_url=\"https://llm-gu39ltmv26zjb2y7.cn-beijing.maas.aliyuncs.com/compatible-mode/v1\",\n    temperature=0\n)",
  "storage": {
    "mysql": {
      "version": "8.0.x",
      "deployment": "local Windows Docker Desktop",
      "container_name": "medical-mysql",
      "port": 3306,
      "named_volume": "medical_mysql_data",
      "databases": {
        "medical_ai": "医疗业务数据、模拟患者、医生、病历、检验、影像、药物、病例、AI结果、医生审核结果",
        "medical_ai_graph": "LangGraph Checkpoint、Graph State、HITL 中断恢复、Time Travel"
      }
    },
    "milvus": {
      "status": "reserve_for_rag_phase",
      "deployment": "local Windows Docker Desktop",
      "requirement": "当前可以预留 docker profile 和配置结构，但不要下载医疗数据、不要构建向量库、不要执行批量 Embedding。",
      "future_components": [
        "Milvus",
        "etcd",
        "MinIO"
      ]
    },
    "forbidden_databases": [
      "PostgreSQL",
      "Redis",
      "MongoDB",
      "Elasticsearch"
    ]
  },
  "target_architecture": [
    "Doctor/User",
    "FastAPI",
    "LangGraph Main Diagnosis Graph",
    "Risk Screening",
    "MedicalSupervisor DeepAgent",
    "MCP Patient Tools",
    "RAG Tool Placeholder",
    "Specialist Router",
    "Cardiology SubGraph",
    "Gastroenterology SubGraph",
    "Synthesis",
    "Human-In-the-Loop Doctor Review",
    "Finalize",
    "MySQL Checkpoint",
    "Time Travel"
  ],
  "architecture_responsibilities": {
    "LangGraph": "控制医疗诊断主流程、条件路由、SubGraph、HITL、Checkpoint 和恢复。",
    "DeepAgents": "负责综合病例推理以及工具调用，不负责数据库权限和最终诊断确认。",
    "MCP": "提供患者真实业务数据访问，本阶段全部只读。",
    "RAG": "未来负责医学指南和医学知识证据检索，本阶段只预留接口。",
    "SubGraph": "实现专科诊断子流程。",
    "SubAgent": "负责专科领域分析。",
    "MySQL": "业务持久化以及 LangGraph Checkpoint 持久化。",
    "Human-In-the-Loop": "医生通过、修改或驳回 AI 辅助诊断。",
    "Time Travel": "基于 Checkpoint 查看历史 State 和诊断执行过程。"
  },
  "project_structure": [
    "app/__init__.py",
    "app/main.py",
    "app/core/__init__.py",
    "app/core/config.py",
    "app/core/llm.py",
    "app/core/logging.py",
    "app/api/__init__.py",
    "app/api/diagnosis.py",
    "app/api/cases.py",
    "app/api/review.py",
    "app/graph/__init__.py",
    "app/graph/state.py",
    "app/graph/workflow.py",
    "app/graph/nodes/__init__.py",
    "app/graph/nodes/prepare.py",
    "app/graph/nodes/risk.py",
    "app/graph/nodes/medical_agent.py",
    "app/graph/nodes/specialist.py",
    "app/graph/nodes/synthesis.py",
    "app/graph/nodes/review.py",
    "app/graph/nodes/finalize.py",
    "app/graph/subgraphs/__init__.py",
    "app/graph/subgraphs/cardiology.py",
    "app/graph/subgraphs/gastroenterology.py",
    "app/agents/__init__.py",
    "app/agents/medical.py",
    "app/agents/cardiology.py",
    "app/agents/gastroenterology.py",
    "app/tools/__init__.py",
    "app/tools/patient.py",
    "app/tools/doctor.py",
    "app/tools/knowledge.py",
    "app/mcp/__init__.py",
    "app/mcp/client.py",
    "app/mcp/config.py",
    "app/rag/__init__.py",
    "app/rag/retriever.py",
    "app/schemas/__init__.py",
    "app/schemas/diagnosis.py",
    "app/schemas/patient.py",
    "app/schemas/evidence.py",
    "app/safety/__init__.py",
    "app/safety/risk.py",
    "app/middleware/__init__.py",
    "app/middleware/security.py",
    "app/persistence/__init__.py",
    "app/persistence/database.py",
    "app/persistence/models.py",
    "app/persistence/repositories.py",
    "app/persistence/checkpoint.py",
    "patient_mcp/__init__.py",
    "patient_mcp/server.py",
    "patient_mcp/tools.py",
    "scripts/init_db.py",
    "scripts/seed_demo_data.py",
    "tests/__init__.py",
    "tests/test_llm.py",
    "tests/test_mcp.py",
    "tests/test_graph.py",
    "tests/test_risk.py",
    "tests/test_hitl.py",
    "docker/docker-compose.yml",
    ".env.example",
    ".gitignore",
    "requirements.txt",
    "README.md"
  ],
  "implementation_steps": [
    {
      "step": 1,
      "name": "clean_existing_project",
      "requirements": [
        "检查当前项目，目前只有 PyCharm 默认 main.py 时可以替换。",
        "保留项目根目录，不重新创建第二层 medical-multi-agent 目录。",
        "删除 PyCharm 默认 Hello World 示例代码。",
        "不要删除 IDE 配置以外的用户已有有效代码；若存在新增文件必须先理解后复用。"
      ]
    },
    {
      "step": 2,
      "name": "dependency_baseline",
      "requirements": [
        "建立 requirements.txt。",
        "使用 Python 3.12。",
        "加入 FastAPI、uvicorn、pydantic-settings、langchain、langchain-openai、langgraph、deepagents、langchain-mcp-adapters、SQLAlchemy、Alembic、MySQL async driver、pytest、pytest-asyncio、httpx 等实际需要依赖。",
        "加入 MySQL LangGraph Checkpointer 时必须使用与当前 LangGraph 兼容的实际可用实现并锁版本。",
        "不要加入 PostgreSQL 依赖。",
        "不要加入当前阶段不使用的大量 AI 框架。",
        "安装后执行 import 验证，解决真实依赖冲突。"
      ]
    },
    {
      "step": 3,
      "name": "configuration",
      "requirements": [
        "使用 pydantic-settings 建立统一 Settings。",
        "所有 API Key、密码、数据库地址只能从环境变量读取。",
        "生成 .env.example，不提交真实密钥。",
        "必须支持 ALIYUN_LLM_API_KEY、ALIYUN_LLM_BASE_URL、ALIYUN_LLM_MODEL、MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DATABASE、MYSQL_GRAPH_DATABASE、MCP_SERVER_URL。",
        "默认 LLM model 为 qwen3.5-omni-plus-2026-03-15。",
        "默认 base_url 使用用户提供的阿里 MaaS compatible-mode/v1 地址。"
      ]
    },
    {
      "step": 4,
      "name": "llm_factory",
      "requirements": [
        "在 app/core/llm.py 中统一创建 ChatOpenAI。",
        "禁止在每个 Agent 或 Tool 内重复 new ChatOpenAI。",
        "temperature=0。",
        "提供 get_llm() 或等价单一入口。",
        "支持启动时配置校验。",
        "API Key 不得打印到日志。"
      ]
    },
    {
      "step": 5,
      "name": "mysql_docker",
      "requirements": [
        "docker/docker-compose.yml 默认启动 MySQL 8.0.x。",
        "使用 named volume medical_mysql_data。",
        "暴露 localhost:3306。",
        "restart 使用 unless-stopped。",
        "创建 medical_ai 和 medical_ai_graph 两个 database。",
        "不要创建两个 MySQL 容器。",
        "不要使用 Windows NTFS 目录直接 bind mount MySQL 数据目录。",
        "提供 healthcheck。",
        "不要通过 docker compose down -v 作为正常清理命令。"
      ]
    },
    {
      "step": 6,
      "name": "medical_business_schema",
      "requirements": [
        "使用 SQLAlchemy 2.x 建立最小业务模型。",
        "至少实现 Patient、Doctor、MedicalVisit、LabResult、ImagingReport、Medication、Allergy、MedicalCase、MedicalAssessment。",
        "模型保持最小，不建立复杂医院 HIS 全模型。",
        "Patient 使用模拟编号，不保存真实身份证等敏感字段。",
        "MedicalAssessment 必须保留 ai_result_json、doctor_result_json、review_status、reviewer_id、reviewed_at。",
        "MedicalCase 至少保留 id、patient_id、thread_id、question、status、risk_level、created_at、updated_at。",
        "使用 Alembic 或明确的初始化脚本建立表结构。"
      ]
    },
    {
      "step": 7,
      "name": "demo_medical_data",
      "requirements": [
        "建立 seed_demo_data.py。",
        "生成若干完全虚构的患者、医生和病历数据。",
        "至少准备一个心内科测试病例：胸痛、高血压史、相关检查信息。",
        "至少准备一个消化科测试病例：腹痛、恶心或呕吐等。",
        "至少准备一个普通低风险测试病例。",
        "模拟数据必须明显标记为 DEMO，不得包含真实个人信息。"
      ]
    },
    {
      "step": 8,
      "name": "mcp_server",
      "requirements": [
        "建立 patient_mcp MCP Server。",
        "采用当前 MCP 推荐且 langchain-mcp-adapters 实际支持的 Streamable HTTP 方式，不使用已废弃 SSE 方案。",
        "MCP Server 读取 medical_ai MySQL。",
        "实现 get_patient_summary。",
        "实现 get_patient_visits。",
        "实现 get_medical_records 或等价病历查询。",
        "实现 get_lab_results。",
        "实现 get_imaging_reports。",
        "实现 get_medications。",
        "实现 get_allergies。",
        "实现 get_doctor_info。",
        "所有 MCP Tool V1 必须 READ ONLY。",
        "禁止提供 update/delete/prescribe 等写操作。",
        "Tool 返回尽量采用结构化数据而不是大段拼接文本。",
        "处理患者不存在、数据为空、数据库异常。"
      ]
    },
    {
      "step": 9,
      "name": "mcp_client",
      "requirements": [
        "使用 MultiServerMCPClient 或当前版本正确对应方式连接 patient_mcp。",
        "MCP Client 在应用生命周期中正确初始化和复用。",
        "禁止每次 Tool 调用都 asyncio.run() 创建新 event loop。",
        "FastAPI、LangGraph、MCP 整体优先 async。",
        "提供连接超时和清晰异常处理。"
      ]
    },
    {
      "step": 10,
      "name": "rag_placeholder",
      "requirements": [
        "建立 app/rag/retriever.py 和 app/tools/knowledge.py。",
        "定义 search_medical_knowledge(query) 标准接口。",
        "当前不要下载 ModelScope 数据。",
        "当前不要构建 Milvus Collection。",
        "当前不要调用 Embedding API。",
        "当前接口在 RAG 未启用时返回结构化状态，例如 enabled=false、evidence=[]、message='RAG knowledge base is not configured yet'。",
        "Medical Agent 必须能够在 RAG 未配置时继续工作，但最终结果明确标记当前没有外部 RAG 证据。",
        "后续 RAG 实现不得要求重写 Graph 和 Agent，只替换 retriever 内部实现即可。"
      ]
    },
    {
      "step": 11,
      "name": "structured_output",
      "requirements": [
        "定义 DiagnosisResult Pydantic 模型。",
        "至少包含 clinical_summary、key_findings、possible_conditions、red_flags、missing_information、recommended_tests、recommended_department、risk_level、evidence、rag_enabled、disclaimer。",
        "PossibleCondition 至少包含 name、reason、confidence 或等价字段。",
        "risk_level 固定 low、medium、high、emergency。",
        "避免 Agent 最终只返回自由 Markdown。",
        "患者病历事实、模型推理和 RAG Evidence 在结构上尽量分开。"
      ]
    },
    {
      "step": 12,
      "name": "medical_supervisor_agent",
      "requirements": [
        "使用 create_deep_agent 创建 MedicalSupervisorAgent。",
        "复用统一 LLM。",
        "可调用患者 MCP Tool、医生信息 Tool、RAG Tool。",
        "System Prompt 明确：不得创造不存在的患者病史、检查和检验数据。",
        "患者事实只能来自当前输入或 MCP 返回。",
        "RAG Evidence 只能来自 search_medical_knowledge 返回，禁止编造 chunk_id、document_id 或指南名称。",
        "RAG 未启用时允许基于模型医学知识给出辅助分析，但必须明确缺少外部知识证据。",
        "必须区分辅助诊断与最终临床诊断。",
        "必须生成符合 DiagnosisResult 的结构化结果。",
        "Agent 不得直接执行 SQL。",
        "Agent 不得修改医疗业务数据。"
      ]
    },
    {
      "step": 13,
      "name": "specialist_agents",
      "requirements": [
        "建立 CardiologyAgent 和 GastroenterologyAgent。",
        "不要复制完全相同的 Supervisor Prompt。",
        "CardiologyAgent 只负责心血管相关专业分析。",
        "GastroenterologyAgent 只负责消化系统相关专业分析。",
        "专科 Agent 输入使用主 Graph 已整理的病例上下文。",
        "专科 Agent 输出结构化 SpecialistOpinion。",
        "V1 只做这两个专科 Agent，不增加更多科室。"
      ]
    },
    {
      "step": 14,
      "name": "specialist_subgraphs",
      "requirements": [
        "CardiologyAgent 必须通过 Cardiology SubGraph 接入，而不是主 Graph 直接裸调用。",
        "GastroenterologyAgent 必须通过 Gastroenterology SubGraph 接入。",
        "每个 SubGraph 保持最小：prepare_specialist_context -> specialist_agent -> specialist_result。",
        "SubGraph 输出回到主 Graph State。",
        "不要在 SubGraph 中重复完整主流程。"
      ]
    },
    {
      "step": 15,
      "name": "graph_state",
      "requirements": [
        "定义明确 DiagnosisState，不允许所有业务状态全部塞入 messages。",
        "至少包含 case_id、thread_id、patient_id、user_query、intent、patient_context、risk_level、red_flags、rag_evidence、draft_assessment、specialist_opinions、doctor_review、final_assessment、errors。",
        "messages 仅用于模型交互，不作为业务数据库。",
        "State 内容必须可序列化，以支持 Checkpoint。"
      ]
    },
    {
      "step": 16,
      "name": "risk_screening",
      "requirements": [
        "实现最小 Safety 层。",
        "使用确定性 Python 规则优先识别严重胸痛、严重呼吸困难、意识障碍、卒中征象、严重出血、严重过敏等红旗信号。",
        "不要引入复杂规则引擎。",
        "高风险信号必须在调用多个专科 Agent 前执行。",
        "命中 emergency 时在结果中明显标识紧急医疗风险。",
        "风险规则不能直接声称疾病确诊。"
      ]
    },
    {
      "step": 17,
      "name": "main_langgraph",
      "requirements": [
        "建立 StateGraph(DiagnosisState)。",
        "主流程固定为 START -> prepare -> risk_screening -> medical_agent -> specialist_router -> optional specialist subgraph -> synthesis -> doctor_review -> finalize -> END。",
        "specialist_router 使用 Conditional Edge。",
        "能够路由 cardiology、gastroenterology 或 none。",
        "不要让 DeepAgent 取代 LangGraph 主流程。",
        "LangGraph 负责确定性流程，Agent 负责推理。"
      ]
    },
    {
      "step": 18,
      "name": "human_in_the_loop",
      "requirements": [
        "doctor_review 节点必须使用 LangGraph interrupt() 或当前版本正式等价机制。",
        "必须支持 approve、edit、reject 三种操作。",
        "approve 使用 AI Draft 继续。",
        "edit 保存医生修改后的结构化结果。",
        "reject 保存驳回状态和可选原因。",
        "通过 Command(resume=...) 或当前版本正确恢复机制继续执行。",
        "未经医生审核禁止进入 FINAL。"
      ]
    },
    {
      "step": 19,
      "name": "mysql_checkpoint",
      "requirements": [
        "LangGraph Checkpoint 存放在 medical_ai_graph MySQL database。",
        "优先使用经过验证、兼容当前 LangGraph 的 MySQL Checkpointer。",
        "初始化时执行所需 setup/migration。",
        "thread_id 使用 case_id 或与 case_id 一一对应的稳定值。",
        "必须验证 graph invoke 后产生 checkpoint。",
        "必须验证 interrupt 后进程重启仍可通过同一 thread_id 恢复。",
        "若所选社区 MySQL Checkpointer 与当前 LangGraph 版本不兼容，不允许静默改用 PostgreSQL；应选择兼容版本组合并锁定。"
      ]
    },
    {
      "step": 20,
      "name": "time_travel",
      "requirements": [
        "提供查询指定 case/thread 历史 checkpoint 的服务方法。",
        "提供 API 查看诊断过程历史 State 摘要。",
        "至少能够看到 prepare、risk、medical_agent、specialist、review 等主要阶段产生的历史状态。",
        "不要把 Time Travel 理解为覆盖正式医疗历史。",
        "如果实现 fork/replay，必须产生新的执行分支或版本，不覆盖原 FINAL。"
      ]
    },
    {
      "step": 21,
      "name": "middleware",
      "requirements": [
        "仅实现当前真正需要的 Middleware。",
        "加入 PII 脱敏能力，重点防止日志和模型输出泄露手机号、邮箱等直接身份信息。",
        "加入 Model Call Limit。",
        "加入 Tool Call Limit。",
        "不要堆大量无业务价值 Middleware。",
        "如果具体 Middleware 类在当前 LangChain/DeepAgents 版本 API 有变化，按当前真实 API 实现。"
      ]
    },
    {
      "step": 22,
      "name": "fastapi_endpoints",
      "requirements": [
        "GET /health：应用健康检查。",
        "POST /api/v1/diagnoses：创建病例并启动 LangGraph。",
        "GET /api/v1/cases/{case_id}：查询病例及当前状态。",
        "POST /api/v1/cases/{case_id}/review：医生 approve/edit/reject 并恢复 Graph。",
        "GET /api/v1/cases/{case_id}/history：查询 Checkpoint/Time Travel 历史摘要。",
        "接口必须使用 Pydantic request/response schema。",
        "返回明确 HTTP 状态码和错误信息。",
        "不得把 Python traceback 原样返回给客户端。"
      ]
    },
    {
      "step": 23,
      "name": "logging_and_security",
      "requirements": [
        "使用标准 Python logging 建立结构化、易定位日志。",
        "至少记录 case_id、thread_id、graph node、tool name、duration、status。",
        "日志不得打印 API Key。",
        "日志避免输出完整患者敏感病历。",
        "数据库异常、MCP异常、模型异常必须保留可定位错误。",
        "不要在代码中硬编码数据库密码或 API Key。"
      ]
    },
    {
      "step": 24,
      "name": "tests",
      "requirements": [
        "编写真实 pytest 测试，不允许只创建空测试文件。",
        "测试风险规则。",
        "测试 MySQL Repository。",
        "测试 MCP Tool 能读取 DEMO 患者。",
        "测试患者不存在。",
        "测试 Graph 基础流程。",
        "测试心内科路由。",
        "测试消化科路由。",
        "测试 interrupt。",
        "测试 approve 恢复。",
        "测试 edit 恢复。",
        "测试 reject。",
        "测试 Checkpoint 持久化。",
        "测试服务重启后按 thread_id 恢复。",
        "测试 history 能获取多个 checkpoint。",
        "对真实 LLM API 测试使用明确 integration marker，普通单元测试不要每次消耗线上 Token。"
      ]
    },
    {
      "step": 25,
      "name": "readme",
      "requirements": [
        "README.md 用中文。",
        "说明项目定位为医疗辅助诊断，不是自主诊断系统。",
        "说明 Python 3.12 环境。",
        "说明 Docker Desktop MySQL 启动方式。",
        "说明 .env 配置。",
        "说明初始化数据库和 DEMO 数据。",
        "说明启动 patient_mcp。",
        "说明启动 FastAPI。",
        "给出一个完整胸痛 DEMO 请求。",
        "给出医生 review 请求。",
        "说明 Checkpoint 和 Time Travel 测试方式。",
        "说明 RAG 当前处于预留阶段，后续开发到该阶段再选择医疗数据集和构建 Milvus。"
      ]
    }
  ],
  "main_graph": {
    "nodes": [
      "prepare",
      "risk_screening",
      "medical_agent",
      "specialist_router",
      "cardiology_subgraph",
      "gastroenterology_subgraph",
      "synthesis",
      "doctor_review",
      "finalize"
    ],
    "flow": "START -> prepare -> risk_screening -> medical_agent -> specialist_router -> optional specialist subgraph -> synthesis -> doctor_review(interrupt) -> finalize -> END"
  },
  "agent_design": {
    "MedicalSupervisorAgent": {
      "framework": "DeepAgents create_deep_agent",
      "tools": [
        "get_patient_records",
        "get_doctor_info",
        "search_medical_knowledge"
      ],
      "responsibility": "综合患者数据、当前问题和可用医学证据形成结构化辅助诊断草稿，并决定是否建议专科分析。"
    },
    "CardiologyAgent": {
      "responsibility": "心血管病例专业辅助分析。",
      "integration": "Cardiology SubGraph"
    },
    "GastroenterologyAgent": {
      "responsibility": "消化系统病例专业辅助分析。",
      "integration": "Gastroenterology SubGraph"
    }
  },
  "mcp_rules": [
    "MCP 是患者真实医疗业务数据访问层。",
    "MCP Server 直接查询 MySQL medical_ai。",
    "主 Agent 不允许直接访问 SQLAlchemy Repository。",
    "所有医疗数据写操作 V1 禁止暴露为 MCP Tool。",
    "患者不存在必须返回明确结构化结果，而不是让 LLM 猜测。",
    "MCP Tool 返回的数据必须包含必要时间信息，例如 visit_time、observed_at，避免模型混淆旧数据和当前数据。"
  ],
  "medical_safety_rules": [
    "不得把系统称为自动医生。",
    "不得允许未经审核的 AI_DRAFT 自动成为 FINAL。",
    "不得伪造患者病历、检查、检验、医生信息。",
    "不得伪造 RAG Evidence。",
    "不得让用户输入任意 patient_id 后绕过后端授权设计；即使 V1 是 DEMO，也把 patient_id 访问封装在服务层。",
    "所有可能疾病使用辅助判断、可能性、鉴别方向等表达。",
    "高危信号优先提醒医生。",
    "输出包含明确 disclaimer：结果仅用于医生辅助决策，不能替代临床诊断。"
  ],
  "rag_phase_policy": {
    "current_status": "deferred",
    "do_now": [
      "保留 rag package",
      "保留 search_medical_knowledge Tool",
      "保留 KnowledgeEvidence schema",
      "保留 Milvus 配置入口",
      "保证 Agent 在 RAG disabled 时正常运行"
    ],
    "do_not_do_now": [
      "不要访问 ModelScope 搜索医疗数据",
      "不要下载医疗数据集",
      "不要决定最终 chunk_size",
      "不要批量 Embedding",
      "不要构建真实 Milvus Collection",
      "不要确定最终 Embedding 模型调用实现",
      "不要确定最终 Rerank 参数"
    ],
    "future": "等项目真正开发到 RAG 阶段，再根据实际医疗数据重新分析数据源、License、清洗、分片、Embedding、Milvus Schema、召回和 Rerank。"
  },
  "docker_policy": {
    "default_services": [
      "mysql"
    ],
    "optional_rag_profile_future": [
      "milvus",
      "etcd",
      "minio"
    ],
    "volume_policy": "数据库必须使用 Docker named volume。",
    "windows_policy": "开发环境数据库全部运行于 Windows Docker Desktop/WSL2，不直接安装到 Windows 系统。"
  },
  "required_demo_flow": [
    "启动 MySQL。",
    "初始化 medical_ai 和 medical_ai_graph。",
    "导入 DEMO 患者和医生数据。",
    "启动 patient_mcp。",
    "启动 FastAPI。",
    "调用 POST /api/v1/diagnoses，输入一个 DEMO 心内科病例。",
    "LangGraph 执行 prepare 和 risk_screening。",
    "MedicalSupervisor DeepAgent 调用 MCP 获取患者历史数据。",
    "RAG Tool 当前返回 disabled，不阻断流程。",
    "MedicalSupervisor 输出结构化 AI_DRAFT。",
    "Router 进入 Cardiology SubGraph。",
    "CardiologyAgent 输出专业意见。",
    "Synthesis 形成辅助诊断草稿。",
    "doctor_review interrupt 暂停。",
    "调用 review API approve 或 edit。",
    "Graph 从 MySQL Checkpoint 恢复。",
    "finalize 保存 FINAL。",
    "history API 能查看诊断过程 Checkpoint。"
  ],
  "acceptance_criteria": [
    "项目必须能够在 Windows Python 3.12 环境安装依赖。",
    "docker compose 能正常启动 MySQL 并通过 healthcheck。",
    "MySQL 重启或容器重建但不删除 volume 后数据仍存在。",
    "medical_ai 与 medical_ai_graph 职责分离。",
    "FastAPI 能正常启动且 /health 返回成功。",
    "阿里 qwen3.5-omni-plus-2026-03-15 可通过统一 LLM Factory 调用。",
    "patient_mcp 能正常启动并读取 DEMO MySQL 数据。",
    "主 Agent 能通过 MCP 获取患者数据，而不是自己编造。",
    "LangGraph 主流程真实可执行。",
    "DeepAgent 被真实用于 MedicalSupervisor，不是只创建文件占位。",
    "CardiologyAgent 和 GastroenterologyAgent 能通过 SubGraph 执行。",
    "Structured Output 能通过 Pydantic 校验。",
    "高风险病例能被 risk_screening 提前识别。",
    "AI_DRAFT 必须在 doctor_review 节点 interrupt。",
    "approve、edit、reject 均真实可执行。",
    "Checkpoint 真正写入 MySQL。",
    "服务进程重启后能够通过 thread_id 恢复被 interrupt 的病例。",
    "history 接口能读取历史 checkpoint。",
    "能够演示 Time Travel 所需历史 State。",
    "RAG 未配置时系统仍可运行并明确 evidence 为空。",
    "当前实现不得下载 ModelScope 数据。",
    "所有核心测试通过。",
    "README 中所有启动命令按顺序执行能够跑通 DEMO。",
    "无真实 API Key、MySQL 密码或患者隐私被提交到代码仓库。",
    "不得留下影响主流程运行的 TODO、pass 或未实现异常。"
  ],
  "execution_rules": [
    "先检查项目现状，再修改。",
    "按阶段实现并在每个阶段运行测试。",
    "遇到第三方 API 版本差异时读取已安装包源码、类型签名或官方包内接口确认，不允许凭印象伪造调用方式。",
    "如果某个依赖与 Python 3.12 不兼容，选择稳定兼容版本，不降低到 Python 3.10。",
    "如果 DeepAgents 与 LangChain/LangGraph 存在版本约束冲突，选择一组能实际 import 和运行的兼容版本并锁定。",
    "MySQL Checkpointer 必须经过实际 interrupt/resume/restart 测试后才算完成。",
    "不要因为某个非核心可选组件暂时不可用而把主项目改成不同架构。",
    "不要提前实现前端页面。",
    "不要提前进入 RAG 数据集构建阶段。",
    "完成后运行测试、启动检查和 DEMO 链路验证。"
  ],
  "final_report": {
    "required": true,
    "content": [
      "列出新增和修改的关键文件。",
      "列出最终锁定的核心依赖版本。",
      "说明 MySQL、MCP、LangGraph、DeepAgent、SubGraph、Checkpoint、HITL、Time Travel 分别如何实际落地。",
      "给出项目启动顺序。",
      "给出完整 DEMO 调用方式。",
      "列出测试结果。",
      "明确指出 RAG 当前只是预留接口，尚未选择和下载 ModelScope 数据。",
      "如果存在未解决问题，必须明确列出，禁止用假实现冒充完成。"
    ]
  }
}
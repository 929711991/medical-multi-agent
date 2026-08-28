# 医疗辅助多智能体：业务流程与代码技术流程

本文严格依据当前项目代码整理，用于从业务视角和代码视角理解一次医疗辅助诊断如何创建、暂停、审核、恢复、持久化与查询。

> 系统定位：AI 只生成医生辅助决策草稿，不生成无需审核的最终临床诊断。所有数据均为虚构 DEMO 数据。

## 一、整体业务参与者与边界

```mermaid
flowchart LR
    User["医生或系统使用者"]
    API["医疗辅助诊断 API"]
    AI["AI 辅助分析流程"]
    Reviewer["具备 DEMO 编号的审核医生"]
    Final["审核后的最终结果"]

    User -->|"提交 DEMO 患者编号和问题"| API
    API -->|"启动诊断图"| AI
    AI -->|"生成 AI_DRAFT"| Reviewer
    Reviewer -->|"approve：通过"| Final
    Reviewer -->|"edit：修改后通过"| Final
    Reviewer -->|"reject：驳回"| Final

    AI -.->|"不得直接成为 FINAL"| Final
```

业务边界：

- 当前只允许访问以 `DEMO-` 开头且确实存在于数据库中的虚构患者。
- AI 只能读取患者数据，不允许通过 MCP 更新病历、删除记录或开具处方。
- 确定性风险规则先于专科智能体运行，高危结果不能被后续模型降级。
- RAG 未配置时诊断流程仍可继续，但结果必须明确 `rag_enabled=false`、`evidence=[]`。
- `doctor_review` 必须触发 LangGraph 中断；只有审核 API 才能恢复流程。

## 二、完整业务流程

```mermaid
flowchart TD
    Start(["开始"])
    Submit["提交 patient_id 和医疗问题"]
    Access{"是否为允许访问的 DEMO 患者？"}
    NotFound["返回 404：未找到患者"]
    CreateCase["创建 MedicalCase 和待审核 MedicalAssessment"]
    InitState["生成 case_id；thread_id 与 case_id 一一对应"]
    Prepare["prepare：初始化 DiagnosisState"]
    Risk["risk_screening：确定性红旗规则"]
    Emergency{"是否命中 emergency？"}
    Warning["保留紧急风险和红旗；后续模型不得降级"]
    MCP["通过 MCP 获取患者完整病历"]
    Supervisor["MedicalSupervisor DeepAgent 综合分析"]
    Rag["RAG 工具返回 enabled=false 和空证据"]
    Route{"specialist_router 专科路由"}
    Cardio["Cardiology SubGraph"]
    Gastro["Gastroenterology SubGraph"]
    NoneRoute["不调用专科 SubGraph"]
    Synthesis["synthesis：合并综合草稿和专科意见"]
    Pending["状态变为 PENDING_REVIEW"]
    Interrupt["doctor_review：interrupt 暂停"]
    SaveDraft["业务库保存 AI 草稿和风险等级"]
    Doctor["医生提交审核"]
    Action{"审核动作"}
    Approve["approve：采用 AI 草稿"]
    Edit["edit：采用医生修改后的结构化结果"]
    Reject["reject：不生成 final_assessment"]
    Resume["Command(resume=...) 恢复同一 thread_id"]
    Finalize["finalize"]
    Final["业务状态 FINAL"]
    Rejected["业务状态 REJECTED"]
    Persist["保存医生结果、审核人、时间和原因"]
    History["可通过 history API 查看 Checkpoint 历史"]
    Error["异常：病例状态 ERROR，接口返回 503"]

    Start --> Submit --> Access
    Access -->|"否"| NotFound
    Access -->|"是"| CreateCase --> InitState --> Prepare --> Risk --> Emergency
    Emergency -->|"是"| Warning --> MCP
    Emergency -->|"否"| MCP
    MCP --> Supervisor
    Supervisor -->|"调用知识工具"| Rag
    Rag -->|"返回禁用状态和空证据"| Supervisor
    Supervisor --> Route
    Route -->|"cardiology"| Cardio --> Synthesis
    Route -->|"gastroenterology"| Gastro --> Synthesis
    Route -->|"none"| NoneRoute --> Synthesis
    Synthesis --> Pending --> Interrupt --> SaveDraft --> Doctor --> Action
    Action -->|"approve"| Approve --> Resume
    Action -->|"edit"| Edit --> Resume
    Action -->|"reject"| Reject --> Resume
    Resume --> Finalize
    Finalize -->|"approve 或 edit"| Final --> Persist --> History
    Finalize -->|"reject"| Rejected --> Persist --> History

    Prepare -.->|"任一图节点异常"| Error
    Risk -.->|"异常"| Error
    MCP -.->|"异常"| Error
    Supervisor -.->|"异常"| Error
```

## 三、业务状态流转

业务库状态和图内状态是两套相关但不同的状态。业务库不会持久化中间的 `RUNNING`；`RUNNING` 只存在于 Checkpoint 保存的 `DiagnosisState` 中。

### 3.1 `MedicalCase.status` 业务库状态

```mermaid
stateDiagram-v2
    [*] --> CREATED: 创建病例
    CREATED --> PENDING_REVIEW: 图中断后保存 AI_DRAFT
    CREATED --> ERROR: 图、MCP、数据库或模型异常
    PENDING_REVIEW --> FINAL: approve
    PENDING_REVIEW --> FINAL: edit
    PENDING_REVIEW --> REJECTED: reject
    FINAL --> [*]
    REJECTED --> [*]
    ERROR --> [*]
```

### 3.2 `DiagnosisState.status` 图内状态

```mermaid
stateDiagram-v2
    [*] --> RUNNING: prepare
    RUNNING --> PENDING_REVIEW: synthesis
    PENDING_REVIEW --> FINAL: approve 或 edit 后 finalize
    PENDING_REVIEW --> REJECTED: reject 后 finalize
    FINAL --> [*]
    REJECTED --> [*]
```

状态与数据的关系：

| 业务状态 | 关键数据 | 含义 |
|---|---|---|
| `CREATED` | `MedicalCase`、空的待审核 `MedicalAssessment` | 病例已经创建，图尚未完成 |
| `RUNNING` | `DiagnosisState.status`，仅保存于 Checkpoint | LangGraph 正在运行，不写入 `MedicalCase.status` |
| `PENDING_REVIEW` | `ai_result_json` | 已生成 AI 草稿，等待医生审核 |
| `FINAL` | `doctor_result_json`、`reviewer_id`、`reviewed_at` | 医生已通过或修改后通过 |
| `REJECTED` | `review_reason`、审核信息 | 医生驳回，不生成最终结果 |
| `ERROR` | 病例状态和后端日志 | 流程异常，客户端只收到安全错误摘要 |

## 四、LangGraph 主图与 SubGraph

### 4.1 主诊断图

```mermaid
flowchart LR
    S(["START"])
    P["prepare"]
    R["risk_screening"]
    M["medical_agent"]
    SR["specialist_router"]
    C["cardiology_subgraph"]
    G["gastroenterology_subgraph"]
    SY["synthesis"]
    DR["doctor_review / interrupt"]
    F["finalize"]
    E(["END"])

    S --> P --> R --> M --> SR
    SR -->|"cardiology"| C --> SY
    SR -->|"gastroenterology"| G --> SY
    SR -->|"none"| SY
    SY --> DR --> F --> E
```

主图由 `app/graph/workflow.py` 创建。`StateGraph(DiagnosisState)` 控制确定性流程，DeepAgent 只负责需要模型推理的节点。

### 4.2 两个专科 SubGraph 的共同结构

```mermaid
flowchart LR
    SS(["SubGraph START"])
    PC["prepare_specialist_context"]
    SA["specialist_agent"]
    Result["specialist_result"]
    SE(["SubGraph END"])

    SS --> PC
    PC -->|"患者事实、风险、综合草稿"| SA
    SA -->|"SpecialistOpinion"| Result
    Result -->|"追加到 specialist_opinions"| SE
```

- 心内科子图调用 `CardiologyAgent`，只分析心血管相关事实。
- 消化科子图调用 `GastroenterologyAgent`，只分析消化系统相关事实。
- 两个子图都不会重新执行主流程，也不会直接读数据库。

## 五、代码技术架构图

```mermaid
flowchart TB
    subgraph Client["调用方"]
        Doctor["医生 / PowerShell / API 客户端"]
    end

    subgraph FastAPI["FastAPI 进程：8000"]
        Main["app.main：生命周期和路由注册"]
        DiagnosisAPI["POST /api/v1/diagnoses"]
        ReviewAPI["POST /api/v1/cases/{id}/review"]
        CaseAPI["GET case / history"]
        AccessService["PatientAccessService"]
        CaseRepo["CaseRepository / DoctorRepository"]
        Graph["CompiledStateGraph"]
        State["DiagnosisState"]
        Observe["节点耗时和状态日志"]
        MCPClient["MultiServerMCPClient"]
    end

    subgraph Reasoning["推理层"]
        RiskRules["确定性风险规则"]
        Supervisor["MedicalSupervisor DeepAgent"]
        CardioAgent["Cardiology DeepAgent"]
        GastroAgent["Gastroenterology DeepAgent"]
        Structured["Pydantic Structured Output"]
        Middleware["PII 脱敏、模型限流、工具限流"]
        RAG["RAG 占位工具"]
        LLMFactory["统一 get_llm()"]
    end

    subgraph MCPProcess["patient_mcp 进程：8001"]
        HTTP["Streamable HTTP /mcp"]
        MCPServer["FastMCP 只读工具"]
        PatientRepo["PatientRepository / DoctorRepository"]
    end

    subgraph MySQL["单个 MySQL 8 容器"]
        BusinessDB[("medical_ai\n业务数据")]
        GraphDB[("medical_ai_graph\nCheckpoint 与历史状态")]
    end

    Aliyun["阿里云 MaaS OpenAI Compatible API"]

    Doctor --> Main
    Main --> DiagnosisAPI
    Main --> ReviewAPI
    Main --> CaseAPI
    DiagnosisAPI --> AccessService --> BusinessDB
    DiagnosisAPI --> CaseRepo --> BusinessDB
    ReviewAPI --> CaseRepo
    CaseAPI --> CaseRepo
    DiagnosisAPI --> Graph
    ReviewAPI -->|"Command resume"| Graph
    CaseAPI -->|"aget_state_history"| Graph
    Graph <--> State
    Graph --> RiskRules
    Graph --> Supervisor
    Graph --> CardioAgent
    Graph --> GastroAgent
    Graph --> Observe
    Supervisor --> Structured
    CardioAgent --> Structured
    GastroAgent --> Structured
    Supervisor --> Middleware
    CardioAgent --> Middleware
    GastroAgent --> Middleware
    Supervisor --> RAG
    Supervisor --> MCPClient --> HTTP --> MCPServer --> PatientRepo --> BusinessDB
    Supervisor --> LLMFactory --> Aliyun
    CardioAgent --> LLMFactory
    GastroAgent --> LLMFactory
    Graph <--> GraphDB
```

## 六、创建诊断请求的代码时序

```mermaid
sequenceDiagram
    autonumber
    actor User as 调用方
    participant API as diagnosis.py
    participant Access as PatientAccessService
    participant Biz as medical_ai
    participant Graph as LangGraph
    participant Risk as risk_screening
    participant MCP as MCP Client / Server
    participant Agent as MedicalSupervisor
    participant LLM as 阿里云 LLM
    participant Sub as 专科 SubGraph
    participant CP as medical_ai_graph

    User->>API: POST /api/v1/diagnoses
    API->>Access: 校验 DEMO patient_id
    Access->>Biz: 查询患者是否存在
    Biz-->>Access: 患者存在
    API->>Biz: 创建 MedicalCase 和 MedicalAssessment
    API->>Graph: ainvoke(initial_state, thread_id)
    Graph->>CP: 保存初始和节点 Checkpoint
    Graph->>Risk: 执行确定性风险筛查
    Risk-->>Graph: risk_level 和 red_flags
    Graph->>MCP: get_medical_records(patient_id)
    MCP->>Biz: 只读查询病历、检验、影像等
    Biz-->>MCP: 结构化患者事实
    MCP-->>Graph: patient_context
    Graph->>Agent: 患者事实、问题、确定性风险
    Agent->>LLM: 提交问题、患者上下文和工具定义
    LLM-->>Agent: 请求调用 MCP 或 RAG 工具
    Agent->>MCP: 按工具调用请求读取患者事实
    MCP-->>Agent: 工具结果
    Agent->>LLM: 回传工具结果并请求结构化输出
    LLM-->>Agent: DiagnosisResult
    Agent-->>Graph: draft_assessment
    Graph->>Sub: 按关键词条件路由
    Sub->>LLM: 专科结构化分析
    LLM-->>Sub: SpecialistOpinion
    Sub-->>Graph: specialist_opinions
    Graph->>Graph: synthesis 合并并去重
    Graph->>CP: 保存 PENDING_REVIEW Checkpoint
    Graph-->>API: doctor_review interrupt 后返回状态
    API->>Biz: 保存 AI 草稿和风险等级
    API-->>User: 202 PENDING_REVIEW
```

如果图执行出现异常，接口会把病例状态更新为 `ERROR`，记录内部异常日志，并向客户端返回不包含 traceback 的 503 响应。

## 七、医生审核与中断恢复时序

```mermaid
sequenceDiagram
    autonumber
    actor Doctor as 审核医生
    participant API as review.py
    participant Biz as medical_ai
    participant Graph as LangGraph
    participant CP as medical_ai_graph
    participant Review as doctor_review 节点
    participant Finalize as finalize 节点

    Doctor->>API: POST /cases/{case_id}/review
    API->>Biz: 查询病例、状态和审核医生
    Biz-->>API: PENDING_REVIEW 且医生存在
    API->>Graph: Command(resume=审核数据) + thread_id
    Graph->>CP: 读取中断时的最新 Checkpoint
    CP-->>Graph: 恢复完整 DiagnosisState
    Graph->>Review: interrupt 返回 resume 数据
    Review->>Review: DoctorReviewRequest 校验
    Review-->>Graph: doctor_review
    Graph->>Finalize: 根据 action 生成结果
    alt approve
        Finalize-->>Graph: 使用 AI 草稿，状态 FINAL
    else edit
        Finalize-->>Graph: 使用医生 edited_result，状态 FINAL
    else reject
        Finalize-->>Graph: final_assessment=null，状态 REJECTED
    end
    Graph->>CP: 写入审核后 Checkpoint
    Graph-->>API: 返回最终图状态
    API->>Biz: 保存医生结果、审核状态、原因、人员和时间
    API-->>Doctor: 返回病例最终状态
```

## 八、Checkpoint 与 Time Travel 技术流程

```mermaid
flowchart LR
    Node["任一 LangGraph 节点完成"]
    Saver["AsyncMySaver"]
    CP[("checkpoints\n图状态和元数据")]
    Blobs[("checkpoint_blobs\n通道值二进制数据")]
    Writes[("checkpoint_writes\n节点待处理写入")]
    Interrupt["doctor_review interrupt"]
    Restart["FastAPI 进程重启"]
    Resume["相同 thread_id + Command(resume)"]
    HistoryAPI["GET /cases/{id}/history"]
    History["graph.aget_state_history"]
    Summary["阶段、风险、状态、下一节点、草稿/审核标记"]

    Node --> Saver
    Saver --> CP
    Saver --> Blobs
    Saver --> Writes
    Interrupt --> Saver
    Restart --> Resume
    Resume -->|"读取最新 Checkpoint"| Saver
    HistoryAPI --> History --> Saver --> Summary
```

三个表中的 `checkpoint_ns_hash` 是 Checkpointer 内部使用的 `BINARY(16)` MD5 摘要；`checkpoint_ns_hash_md5` 是项目增加的可视化生成列。二者值一致，但前者必须保留以兼容 Checkpointer 主键和查询。

## 九、应用启动技术流程

```mermaid
sequenceDiagram
    autonumber
    participant Uvicorn
    participant Main as app.main.lifespan
    participant Biz as medical_ai
    participant MCP as MCPClientManager
    participant Saver as AsyncMySaver
    participant GraphDB as medical_ai_graph
    participant Graph as CompiledStateGraph

    Uvicorn->>Main: 启动 FastAPI
    Main->>Main: 配置中文结构化日志
    Main->>Biz: initialize_schema()
    Main->>MCP: 创建并缓存 MCP 客户端管理器
    Main->>Saver: from_conn_string(checkpoint_url)
    Saver->>GraphDB: setup() 创建或迁移 Checkpoint 表
    Main->>GraphDB: 统一排序规则并维护可视化 MD5 列
    Main->>Graph: build_diagnosis_graph(checkpointer)
    Graph-->>Main: 写入 app.state.diagnosis_graph
    Main-->>Uvicorn: 应用就绪
    Uvicorn->>Main: 应用关闭
    Main->>MCP: reset_mcp_manager()
    Main->>Biz: 释放 SQLAlchemy 连接池
```

`patient_mcp` 是独立进程，需要在 FastAPI 前或同时启动。它通过 Streamable HTTP 暴露八个只读工具，并直接读取 `medical_ai`。

## 十、DiagnosisState 数据流

| State 字段 | 首次写入节点 | 主要消费者 | 作用 |
|---|---|---|---|
| `case_id`、`thread_id` | API 初始状态 | 所有节点、日志、Checkpoint | 关联业务病例和图执行线程 |
| `patient_id`、`user_query` | API 初始状态 | 风险、MCP、Agent、路由 | 诊断输入 |
| `patient_context` | `prepare` 占位，`medical_agent` 写入真实数据 | Supervisor、专科 SubGraph | 来自 MCP 的患者事实 |
| `risk_level`、`red_flags` | `risk_screening` | Supervisor、专科、合成、审核 | 确定性安全结论 |
| `draft_assessment` | `medical_agent`，`synthesis` 更新 | 审核、finalize、API | 结构化 AI 草稿 |
| `intent` | `specialist_router` | 条件边 | 决定进入哪个专科子图 |
| `specialist_context` | 专科子图准备节点 | 专科 Agent | 隔离后的专科输入 |
| `specialist_result` | 专科 Agent 节点 | 专科结果节点 | 单次 `SpecialistOpinion` |
| `specialist_opinions` | `prepare` 初始化，专科子图追加 | `synthesis` | 专科意见集合 |
| `rag_evidence` | `medical_agent` | API、审计 | 当前外部证据；V1 为空 |
| `doctor_review` | `doctor_review` 恢复后 | `finalize` | 医生审核动作和内容 |
| `final_assessment` | `finalize` | review API、业务库 | 审核后的最终结构化结果 |
| `status` | `prepare`、`synthesis`、`finalize` | API、历史查询 | 图内业务状态 |
| `messages` | Agent 交互 | DeepAgents | 仅用于模型交互，不作为业务数据库 |

## 十一、代码模块对应关系

| 业务或技术职责 | 代码入口 |
|---|---|
| FastAPI 应用生命周期 | `app/main.py` |
| 创建诊断接口 | `app/api/diagnosis.py` |
| 病例和历史接口 | `app/api/cases.py` |
| 医生审核与恢复接口 | `app/api/review.py` |
| 主 LangGraph | `app/graph/workflow.py` |
| 可序列化业务 State | `app/graph/state.py` |
| 主图节点 | `app/graph/nodes/` |
| 心内科、消化科 SubGraph | `app/graph/subgraphs/` |
| 三个 DeepAgent | `app/agents/` |
| 结构化诊断输出 | `app/schemas/diagnosis.py` |
| 确定性红旗规则 | `app/safety/risk.py` |
| MCP 客户端复用 | `app/mcp/client.py` |
| MCP 服务和八个只读工具 | `patient_mcp/server.py`、`patient_mcp/tools.py` |
| RAG 占位接口 | `app/rag/retriever.py`、`app/tools/knowledge.py` |
| 业务模型和 Repository | `app/persistence/models.py`、`app/persistence/repositories.py` |
| MySQL Checkpointer | `app/persistence/checkpoint.py` |
| Time Travel 历史摘要 | `app/graph/history.py` |
| PII 和调用次数限制 | `app/middleware/security.py` |
| 节点日志和耗时 | `app/core/observability.py` |

## 十二、推荐阅读路径

```mermaid
flowchart LR
    A["1. workflow.py\n看主流程"]
    B["2. state.py\n看共享数据"]
    C["3. nodes/\n看每步输入输出"]
    D["4. subgraphs/\n看专科隔离"]
    E["5. agents/\n看模型职责"]
    F["6. mcp/ 与 patient_mcp/\n看数据工具"]
    G["7. persistence/\n看两类持久化"]
    H["8. api/\n看请求如何驱动图"]

    A --> B --> C --> D --> E --> F --> G --> H
```

理解代码时应始终区分三类数据：

1. `medical_ai` 中的患者事实和业务审核结果；
2. `DiagnosisState` 中一次图执行的可序列化状态；
3. `medical_ai_graph` 中用于恢复和历史查看的 Checkpoint。

任务名称：medical_frontend_clinical_workspace_v1

项目说明：
当前 gpt_mcp2 即 medical-multi-agent 项目。
这是一个医疗辅助多智能体系统，后端已经围绕 FastAPI、LangChain、LangGraph、DeepAgents、MCP、MySQL、SubGraph、Checkpoint、Human-In-the-Loop、Time Travel 等能力建设。

本任务不是单独做一个漂亮的 Vue Demo，而是：
1. 先完整读取并理解当前 medical-multi-agent 后端真实代码。
2. 根据真实后端已有接口、DTO、状态机、LangGraph 工作流设计前端。
3. 如果前端完整工作流需要后端补少量接口，则在不破坏现有架构、不重写历史代码的前提下做最小后端补充。
4. 最终形成一套真实可运行、视觉成熟、医生可实际操作的 AI 医疗辅助诊断工作台。
5. 不允许做成 ChatGPT 套皮聊天页面。
6. 不允许为了前端展示而伪造后端不存在的数据。
7. 不允许过度设计。

==================================================
一、第一步：先彻底审查当前后端
==================================================

在写任何前端代码前，必须递归检查当前 medical-multi-agent 项目。

重点读取：

app/
patient_mcp/
tests/
docker/
requirements.txt
.env.example
README.md

以及实际存在的：

FastAPI Router
Pydantic Schema
SQLAlchemy Model
Repository
LangGraph State
LangGraph Workflow
Graph Node
DeepAgent
MCP Client
MCP Server
Checkpoint
HITL
Case
Patient
Doctor
Review

必须先整理出真实后端调用链：

医生请求
→ FastAPI
→ LangGraph
→ risk_screening
→ MedicalSupervisorAgent
→ MCP / RAG
→ Specialist Router
→ Cardiology / Gastroenterology SubGraph
→ synthesis
→ doctor_review interrupt
→ Command resume
→ FINAL
→ MySQL / Checkpoint

禁止根据旧方案文档直接覆盖现有已经正确实现的代码。

原则：

现有能力能够复用则复用。
只有当前后端确实缺少前端必要接口时才最小新增。

==================================================
二、目标前端定位
==================================================

产品定位：

AI 医疗辅助诊断工作台
Clinical AI Workspace

核心用户：

医生

完整操作链：

登录
→ 首页
→ 查找患者
→ 患者临床档案
→ 发起 AI 辅助诊断
→ 实时查看 AI 分析流程
→ 查看综合诊断
→ 查看专科 Agent 意见
→ 查看医学证据
→ 医生审核
→ 通过 / 修改 / 驳回
→ 最终诊断结果
→ 查看历史病例
→ Checkpoint / Time Travel 诊断复盘

AI 只能生成辅助意见。

未经医生审核的结果不得显示为最终临床诊断。

==================================================
三、前端技术栈
==================================================

使用：

Vue 3
TypeScript
Vite
Element Plus
SCSS
CSS Variables
Vue Router
Pinia
Axios
ECharts
Iconify
Vitest
Vue Test Utils
Playwright

Node：

Node.js 24 LTS

不要引入：

Nuxt
Next.js
React
Tailwind CSS
jQuery
微前端
Electron
复杂低代码框架

Element Plus 负责：

表格
表单
分页
Drawer
Dialog
Tabs
Select
DatePicker
Tooltip
Dropdown

SCSS + CSS Variables 负责整体视觉。

==================================================
四、前端项目位置
==================================================

如果当前仓库是：

medical-multi-agent/

则在项目根目录内部创建：

web/

即：

medical-multi-agent/
├── app/
├── patient_mcp/
├── tests/
├── docker/
└── web/

不要再创建：

medical-multi-agent/medical-multi-agent/

这种重复目录。

最终：

web/
├── src/
├── public/
├── tests/
├── package.json
├── vite.config.ts
├── tsconfig.json
└── .env.example

==================================================
五、前端目录
==================================================

建立：

web/src/
├── main.ts
├── App.vue
│
├── api/
│   ├── auth.ts
│   ├── dashboard.ts
│   ├── patient.ts
│   ├── case.ts
│   ├── diagnosis.ts
│   ├── review.ts
│   └── knowledge.ts
│
├── views/
│   ├── login/
│   │   └── index.vue
│   │
│   ├── dashboard/
│   │   └── index.vue
│   │
│   ├── patient/
│   │   ├── list.vue
│   │   └── detail.vue
│   │
│   ├── case/
│   │   ├── list.vue
│   │   ├── workspace.vue
│   │   └── history.vue
│   │
│   ├── review/
│   │   └── queue.vue
│   │
│   ├── knowledge/
│   │   └── index.vue
│   │
│   └── profile/
│       └── index.vue
│
├── components/
│   ├── clinical/
│   │   ├── PatientHeader.vue
│   │   ├── PatientSummary.vue
│   │   ├── ClinicalTimeline.vue
│   │   ├── LabTable.vue
│   │   ├── LabTrendChart.vue
│   │   ├── MedicationList.vue
│   │   └── AllergyAlert.vue
│   │
│   ├── diagnosis/
│   │   ├── DiagnosisResult.vue
│   │   ├── ConditionCard.vue
│   │   ├── RiskBanner.vue
│   │   ├── SpecialistOpinion.vue
│   │   ├── EvidencePanel.vue
│   │   ├── DiagnosisProgress.vue
│   │   └── DoctorReviewDrawer.vue
│   │
│   └── common/
│       ├── AppPage.vue
│       ├── StatusBadge.vue
│       ├── EmptyState.vue
│       └── ErrorState.vue
│
├── layouts/
│   └── MainLayout.vue
│
├── stores/
│   ├── auth.ts
│   ├── patient.ts
│   ├── case.ts
│   └── app.ts
│
├── composables/
│   ├── useCaseStream.ts
│   ├── usePermission.ts
│   └── usePagination.ts
│
├── router/
│   └── index.ts
│
├── types/
│   ├── auth.ts
│   ├── patient.ts
│   ├── clinical.ts
│   ├── diagnosis.ts
│   └── case.ts
│
├── styles/
│   ├── variables.scss
│   ├── reset.scss
│   ├── element.scss
│   └── global.scss
│
└── utils/
    ├── request.ts
    ├── medical.ts
    └── format.ts

保持这个规模，不继续无意义拆包。

==================================================
六、视觉设计标准
==================================================

设计目标：

现代医疗 SaaS
+
Clinical Workspace
+
AI Copilot

整体要求：

专业
清晰
可信
现代
有高级感
信息密度高但不能拥挤
适合医生长时间使用

禁止：

大面积紫色渐变
玻璃拟态
满屏动画
花哨科技大屏
传统老式 HIS 风格
默认 Element Plus 后台模板感

颜色：

Primary：
#2563EB

Primary Hover：
#1D4ED8

Secondary：
#0F9F95

Background：
#F5F7FA

Surface：
#FFFFFF

Soft Surface：
#F8FAFC

Primary Text：
#172033

Secondary Text：
#667085

Tertiary Text：
#98A2B3

Border：
#E7EAF0

风险：

LOW：
#16A34A

MEDIUM：
#D97706

HIGH：
#EA580C

EMERGENCY：
#DC2626

卡片：

圆角 12px
轻阴影
少边框
充分留白

输入控件：

圆角约 8px

不要让整个系统到处都是蓝色。

红色只用于真正危险场景。

==================================================
七、主布局
==================================================

桌面医生工作站优先。

结构：

┌───────────────┬─────────────────────────────┐
│               │ Header                      │
│ Sidebar       ├─────────────────────────────┤
│ 224px         │                             │
│               │ Content                     │
│               │                             │
└───────────────┴─────────────────────────────┘

屏幕：

>=1440：
完整三栏工作区

1280~1439：
正常布局

<1280：
Sidebar 自动折叠
诊断右侧面板可进入 Drawer

移动端只保证基本可访问，不需要第一版做完整移动诊疗工作台。

==================================================
八、主菜单
==================================================

菜单最终：

首页

患者中心

AI辅助诊断
├── 全部病例
├── 诊断中
├── 待审核
└── 已完成

医学知识

我的工作
└── 我的审核

个人中心

注意：

如果当前 RAG 尚未真正完成：

医学知识菜单必须由 Feature Flag 控制。

例如：

VITE_FEATURE_RAG=false

此时不要显示一个假的知识库。

==================================================
九、登录页
==================================================

路由：

/login

需要：

医生账号
密码
登录按钮
登录错误提示
登录 Loading
登录状态恢复

视觉：

左右分栏。

左侧：

医疗 AI 辅助诊断
Clinical AI Assistant

安全
可解释
医生最终审核

右侧：

欢迎登录

账号
密码

登录

不要使用真实患者照片。

==================================================
十、Dashboard
==================================================

路由：

/dashboard

顶部：

上午好，张医生

今天有 X 个 AI 辅助病例等待您处理。

第一排：

今日病例
待审核
高风险
已完成

第二排：

左：
我的待审核病例

右：
风险提醒

底部：

近 7 日病例趋势

ECharts 简洁折线图即可。

Dashboard 后端建议增加：

GET /api/v1/dashboard/summary

一次返回：

today_cases
pending_reviews
high_risk_cases
completed_cases

如果已有等价 API，直接复用。

不要让前端自己请求四次再计算。

==================================================
十一、患者列表
==================================================

路由：

/patients

功能：

分页
姓名搜索
患者编号搜索
性别过滤
最近就诊过滤

字段：

患者
患者编号
性别
年龄
主要病史
最近就诊
当前病例风险
操作

风险必须代表：

当前相关病例风险

不能把患者历史 HIGH 风险永久作为患者标签。

后端若缺失，最小增加：

GET /api/v1/patients

==================================================
十二、患者详情
==================================================

路由：

/patients/:patientId

PatientHeader：

患者姓名
患者编号
性别
年龄
主要慢性病
最近就诊时间

右侧主按钮：

AI 辅助诊断

Tabs：

概览
就诊记录
检验
影像
用药
过敏
AI病例

采用 Tab Lazy Load。

不要进入患者页面就把全部历史数据一次性请求完。

==================================================
十三、患者概览
==================================================

三栏结构：

患者摘要
临床时间线
重要提醒

必须优先突出：

药物过敏
严重既往史
近期重要异常
当前用药
近期就诊

无数据不能显示空白。

例如：

暂无已记录药物过敏

暂无近期影像检查

==================================================
十四、患者 REST API
==================================================

MCP 给 Agent 使用。

Vue 浏览器绝对不能直接访问 MCP。

如果后端当前没有这些接口，则最小新增：

GET /api/v1/patients

GET /api/v1/patients/{patient_id}

GET /api/v1/patients/{patient_id}/overview

GET /api/v1/patients/{patient_id}/visits

GET /api/v1/patients/{patient_id}/labs

GET /api/v1/patients/{patient_id}/imaging

GET /api/v1/patients/{patient_id}/medications

GET /api/v1/patients/{patient_id}/allergies

这些 API：

FastAPI
→ Service / Repository
→ MySQL

不要：

Vue
→ MCP

也不要：

Vue
→ MySQL

==================================================
十五、检验页面
==================================================

字段：

检验项目
结果
单位
参考范围
异常状态
检查时间

异常显示：

↑
↓

或者：

偏高
偏低

不要只有颜色，必须有文字/图标辅助。

如果一个检验项目有多次历史数据：

点击项目
→ 打开趋势 Drawer
→ ECharts 趋势图

只有一条数据时不要显示伪趋势图。

==================================================
十六、AI辅助诊断 Workspace
==================================================

路由：

/cases/:caseId

这是整个前端最重要页面。

桌面采用三栏：

26% / 48% / 26%

左：

患者临床上下文

中：

AI 辅助诊断

右：

诊断过程 + 医学证据

顶部固定 Case Header。

显示：

case_id
患者
年龄
性别
主诉
风险等级
病例状态

==================================================
十七、临床上下文
==================================================

左侧必须展示：

当前主诉
当前症状
既往史
慢性病
用药
过敏
近期检验
近期影像

不能把患者全部几十年病历全文塞进页面。

使用摘要 + 查看详情。

==================================================
十八、AI结构化结果
==================================================

必须与后端 DiagnosisResult / Pydantic Schema 对齐。

至少展示：

clinical_summary

key_findings

possible_conditions

red_flags

missing_information

recommended_tests

recommended_department

risk_level

specialist_opinions

evidence

rag_enabled

disclaimer

不要把 AI Result 做成普通聊天气泡。

==================================================
十九、鉴别诊断组件
==================================================

每个 PossibleCondition：

疾病/方向名称

判断依据

支持程度

如果后端有 confidence 数字：

不要显示：

92% 准确率

转换为：

较强支持
一般支持
有限支持

避免给医生造成模型概率等于临床概率的误导。

==================================================
二十、风险提示
==================================================

如果：

risk_level = emergency

页面顶部显示固定高优先级 Banner：

⚠ 存在紧急风险征象

检测到可能需要优先处理的临床风险，
请优先进行临床评估，不应等待 AI 流程完成。

emergency 使用红色。

high 深橙。

medium 橙色。

low 绿色。

RiskBanner 必须单独组件化。

==================================================
二十一、缺失信息
==================================================

单独展示：

需要进一步确认

例如：

胸痛是否向左肩放射
是否伴冷汗
是否存在既往心肌梗死史

这一块不能混在普通 AI 文本里。

==================================================
二十二、专科 Agent
==================================================

当前后端已有或计划：

MedicalSupervisorAgent

CardiologyAgent

GastroenterologyAgent

前端显示：

综合医疗 AI

心内科专业分析

消化科专业分析

不要默认向医生显示：

medical_agent

cardiology_subgraph

gastroenterology_subgraph

这些是开发技术名称。

SpecialistOpinion 单独组件。

==================================================
二十三、实时诊断进度
==================================================

医生点击开始 AI 分析后，不能白屏等待几十秒。

前端必须实时展示：

✓ 准备患者资料

✓ 紧急风险筛查

✓ 获取历史病历

✓ 综合医学分析

✓ 心内科专业分析

✓ 生成辅助诊断

● 等待医生审核

建议后端增加 SSE：

GET /api/v1/cases/{case_id}/events

如果当前已有流式接口则复用。

不要为了单向 Graph 状态推送引入 WebSocket。

==================================================
二十四、SSE事件结构
==================================================

后端统一输出类似：

{
  "event": "graph.node.completed",
  "case_id": "CASE001",
  "node": "risk_screening",
  "label": "紧急风险筛查",
  "status": "completed",
  "timestamp": "..."
}

失败：

{
  "event": "graph.node.failed",
  "node": "medical_agent",
  "label": "综合医学分析",
  "status": "failed",
  "message": "AI 服务暂时不可用"
}

禁止把：

Python traceback

Exception repr

数据库连接串

模型 Key

返回到前端。

==================================================
二十五、诊断流程技术/业务双层展示
==================================================

医生模式：

患者资料准备
风险筛查
历史病历分析
综合医学分析
心内科专业分析
医生审核

开发模式：

可额外看到：

LangGraph Node
DeepAgent
MCP Tool
SubGraph
thread_id
checkpoint_id
duration

开发模式只允许开发环境开启。

普通医生页面不能被技术实现细节污染。

==================================================
二十六、医生审核 HITL
==================================================

AI_DRAFT 到达 doctor_review interrupt 后：

页面底部 Sticky：

AI辅助意见 · 等待医生审核

[驳回] [编辑诊断] [审核通过]

三个操作必须真实对接后端：

approve
edit
reject

不允许前端只改显示状态。

==================================================
二十七、医生编辑诊断
==================================================

点击：

编辑诊断

打开约 720px Drawer。

编辑：

临床摘要

鉴别诊断

诊断依据

建议检查

风险等级

医生补充意见

不要让医生直接编辑整个 JSON。

使用真正表单。

医生修改后：

必须同时保留：

AI 原始结果

医生修改结果

不能覆盖 AI 原始数据。

==================================================
二十八、审核并发保护
==================================================

后端增加或确认：

assessment_version

例如：

version = 3

前端提交：

{
  "action": "approve",
  "expected_version": 3
}

或者：

{
  "action": "edit",
  "expected_version": 3,
  "result": {...}
}

如果其他医生已经修改：

返回：

409 Conflict

前端提示：

该病例已被其他医生更新，
请刷新后重新查看最新结果。

这是必须实现的并发保护。

==================================================
二十九、reviewer_id安全
==================================================

绝对禁止：

前端提交 reviewer_id。

错误：

{
  "reviewer_id": 10001,
  "action": "approve"
}

正确：

前端只提交：

{
  "action": "approve",
  "expected_version": 3
}

后端：

JWT / Session
→ get_current_doctor()
→ reviewer_id

==================================================
三十、病例状态机
==================================================

前后端统一：

CREATED

RUNNING

WAITING_REVIEW

FINAL

REJECTED

FAILED

正常：

CREATED
→ RUNNING
→ WAITING_REVIEW
→ FINAL

或者：

WAITING_REVIEW
→ REJECTED

失败：

RUNNING
→ FAILED

不要让前端自己根据字段组合推测病例状态。

==================================================
三十一、病例列表
==================================================

路由：

/cases

Tabs：

全部
诊断中
待审核
已完成
已驳回
执行失败

字段：

病例号
患者
主诉
专科
风险
状态
创建时间
更新时间

支持：

患者搜索
状态筛选
风险筛选
时间筛选
分页

==================================================
三十二、待审核队列
==================================================

路由：

/reviews

按优先级排序：

EMERGENCY
HIGH
MEDIUM
LOW

相同风险：

等待最久的排前面。

卡片或列表显示：

风险
病例号
患者
年龄
主诉
专业分析
AI完成时间
等待时间

按钮：

立即审核

==================================================
三十三、Checkpoint / Time Travel
==================================================

路由：

/cases/:caseId/history

必须做成业务 Timeline。

例如：

10:21
病例创建

10:21
风险筛查
HIGH

10:22
读取历史病历
8次就诊记录

10:22
AI综合分析

10:23
心内科专业分析

10:24
生成AI辅助意见

10:30
张医生修改结果

10:30
最终确认

点击节点：

查看当时状态摘要。

医生模式不要直接显示完整 Checkpoint JSON。

==================================================
三十四、AI / 医生结果对比
==================================================

History 页面增加：

AI原始意见
VS
医生最终意见

展示：

新增
删除
修改

至少支持：

临床摘要差异

possible_conditions 差异

风险等级差异

建议检查差异

医生补充意见

这将用于：

医生复盘

模型效果分析

后续 Prompt 优化

==================================================
三十五、患者 AI Copilot
==================================================

患者详情提供：

✨ 询问 AI

打开 Drawer。

支持：

总结最近三次就诊

最近有哪些异常检验？

患者当前正在使用哪些药物？

有哪些药物过敏？

近一年血压控制情况如何？

请求链：

Vue
→ FastAPI
→ Agent
→ MCP
→ MySQL

此能力只用于：

患者信息整理 / 查询

不能直接将回答保存为正式诊断。

==================================================
三十六、RAG / 医学证据
==================================================

RAG 当前如果尚未完成：

rag_enabled = false

显示：

当前未启用外部医学知识库

不要显示假证据。

以后 RAG 启用后：

EvidencePanel 显示：

指南名称

来源机构

版本

章节

证据摘要

查看原始证据

开发模式才显示：

chunk_id

document_id

retrieval_score

vector 等技术字段。

==================================================
三十七、认证
==================================================

如果当前后端没有登录能力：

最小增加：

POST /api/v1/auth/login

POST /api/v1/auth/logout

GET /api/v1/auth/me

使用 JWT / Session。

推荐：

HttpOnly
Secure
SameSite=Lax

Cookie。

不要把长期身份 Token 存：

localStorage

不要让前端能够伪造 doctor_id。

第一版角色：

doctor

admin 如果当前确有管理需求再保留。

不要设计复杂 RBAC。

==================================================
三十八、前端访问权限
==================================================

路由守卫：

未登录访问业务页：

→ /login

401：

清理前端登录态
→ /login

403：

显示无权限页面/提示

前端权限只用于：

UI显示控制。

真正权限必须由后端验证。

==================================================
三十九、API统一响应
==================================================

如果当前后端响应已经统一，优先复用。

如果没有，则最小统一为：

{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "..."
}

分页：

{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 100
  },
  "request_id": "..."
}

不要同时出现：

rows
result
records
list
data

多个不同规范。

==================================================
四十、错误状态
==================================================

统一处理：

400：
参数错误

401：
登录失效

403：
无权限

404：
不存在

409：
数据版本冲突

422：
业务输入校验

429：
调用过于频繁

500：
系统错误

502/503：
AI / MCP 服务不可用

不得向前端输出：

Traceback
SQL
数据库地址
API Key
完整内部异常

==================================================
四十一、AI失败处理
==================================================

如果 LLM / MCP / Graph 节点失败：

病例不能消失。

页面显示：

AI分析暂时失败

病例数据已经保存，
可稍后重试。

如果当前后端已有安全重试 API：

复用。

没有则先只提供：

刷新状态

不要为了 V1 建复杂异步任务系统。

==================================================
四十二、前端安全
==================================================

禁止直接：

<div v-html="aiResult"></div>

模型输出
病历
RAG文本
MCP文本

全部视为不可信输入。

优先使用：

结构化字段
纯文本渲染

如果以后支持 Markdown：

Markdown Parser
+
DOMPurify

==================================================
四十三、隐私
==================================================

前端 console 不打印：

完整患者对象

完整病历

JWT

Cookie

模型 Key

Checkpoint 原始 State

生产环境关闭开发日志。

敏感字段按需求支持：

手机号脱敏

身份证不应出现在当前 V1 普通页面

==================================================
四十四、Loading / Empty / Error
==================================================

每个核心页面必须具备：

Loading

Empty

Error

Success

使用 Skeleton。

禁止：

空白区域

无限 Spinner

没有错误信息

例如：

无过敏：

暂无已记录药物过敏

RAG未启用：

当前未启用外部医学知识库

无历史病例：

暂无 AI 辅助诊断记录

==================================================
四十五、性能
==================================================

患者详情：

先加载 overview。

其他 Tabs Lazy Load。

病例列表分页。

检验结果分页或按日期范围查询。

不要一次把患者全部历史病历加载进浏览器。

组件按路由拆包。

ECharts 按需加载。

==================================================
四十六、Pinia
==================================================

Pinia 只保存：

登录用户

当前 patient 的必要摘要

当前 case 的必要状态

全局 UI 状态

不要长期缓存：

所有患者

所有检验

所有病历

所有 Case

页面数据正常按 API 生命周期重新获取。

==================================================
四十七、TypeScript DTO
==================================================

必须根据后端真实 Pydantic Schema 建立 TypeScript Interface。

不得手写一个和后端字段不同的假 DTO。

核心至少：

Patient

PatientOverview

Visit

LabResult

ImagingReport

Medication

Allergy

MedicalCase

DiagnosisResult

PossibleCondition

SpecialistOpinion

Evidence

ReviewRequest

CheckpointHistoryItem

DashboardSummary

==================================================
四十八、字段命名
==================================================

网络 DTO 建议与 Python 后端一致：

snake_case

例如：

clinical_summary

key_findings

possible_conditions

risk_level

recommended_tests

不要为了 camelCase 再引入一层没有必要的数据转换。

==================================================
四十九、后端建议最终补齐的 API
==================================================

先检查已有接口。

只有缺失才新增。

认证：

POST /api/v1/auth/login

POST /api/v1/auth/logout

GET /api/v1/auth/me

Dashboard：

GET /api/v1/dashboard/summary

Patient：

GET /api/v1/patients

GET /api/v1/patients/{patient_id}

GET /api/v1/patients/{patient_id}/overview

GET /api/v1/patients/{patient_id}/visits

GET /api/v1/patients/{patient_id}/labs

GET /api/v1/patients/{patient_id}/imaging

GET /api/v1/patients/{patient_id}/medications

GET /api/v1/patients/{patient_id}/allergies

Case：

POST /api/v1/diagnoses

GET /api/v1/cases

GET /api/v1/cases/{case_id}

GET /api/v1/cases/pending-review

GET /api/v1/cases/{case_id}/events

POST /api/v1/cases/{case_id}/review

GET /api/v1/cases/{case_id}/history

如果已有等价路由：

复用已有路由。

不要创建重复 API。

==================================================
五十、禁止浏览器直接访问
==================================================

绝对禁止前端直接访问：

MySQL

Milvus

MCP Server

Qwen API

LangGraph Checkpoint 数据库

Embedding API

Rerank API

所有这些必须由 FastAPI 后端统一隔离。

==================================================
五十一、开发环境
==================================================

Windows：

前端：

http://localhost:5173

FastAPI：

http://localhost:8000

Docker：

MySQL

Milvus 后期启用

Vite development proxy：

/api
→ http://localhost:8000

避免开发阶段 CORS 混乱。

==================================================
五十二、生产部署
==================================================

Vue：

npm run build

产出：

dist/

Nginx：

/
→ Vue Dist

/api/
→ FastAPI

SSE 路径需要：

proxy_http_version 1.1

proxy_buffering off

避免诊断进度被 Nginx 缓冲后一次性返回。

==================================================
五十三、测试要求
==================================================

前端必须有真实测试。

Vitest：

RiskBadge

DiagnosisResult

ConditionCard

DoctorReviewDrawer

状态转换

API错误处理

Playwright：

医生登录

患者搜索

进入患者详情

发起AI辅助诊断

进入Case Workspace

等待WAITING_REVIEW

Approve

Edit

Reject

病例列表

History

409审核冲突

401重新登录

RAG disabled 显示

不能只生成测试文件不写断言。

==================================================
五十四、UI验收
==================================================

必须检查：

1440x900

1920x1080

2560x1440

不允许：

表格溢出

按钮遮挡

三栏高度崩坏

Drawer超出屏幕

文字严重截断

过多横向滚动

页面整体必须保持：

专业
清爽
统一
稳定

==================================================
五十五、功能验收
==================================================

最终至少完成：

医生登录

首页统计

患者搜索

患者列表

患者详情

患者临床概览

历史就诊

检验结果

检验趋势

影像报告

用药

过敏

患者AI Copilot

创建AI病例

AI诊断工作台

实时AI流程

风险提醒

临床摘要

关键发现

鉴别诊断

缺失信息

建议检查

建议科室

心内科Agent意见

消化科Agent意见

RAG状态

医学证据预留

医生Approve

医生Edit

医生Reject

并发审核冲突保护

病例列表

待审核队列

诊断失败状态

Checkpoint历史

Time Travel轨迹

AI原始结果与医生结果对比

登录失效处理

Loading

Empty

Error

权限控制

==================================================
五十六、后端保护要求
==================================================

本次允许根据前端需要修改后端，但必须遵守：

不要重构整个后端。

不要修改已经正确工作的 LangGraph 主流程。

不要重写 DeepAgent。

不要重写 MCP。

不要修改 SubGraph 业务边界。

不要为了前端直接暴露数据库。

不要为了前端绕过 HITL。

不要让 AI_DRAFT 直接 FINAL。

不要新增 Redis。

不要新增 PostgreSQL。

不要新增 MongoDB。

不要新增 Elasticsearch。

不要新增 Kafka。

不要新增 RabbitMQ。

不要新增 Kubernetes。

只允许做：

API补齐

认证补齐

DTO补齐

SSE进度补齐

审核版本控制

必要的Repository查询

必要的Dashboard聚合

==================================================
五十七、RAG当前策略
==================================================

不要因为前端有“医学知识”页面就提前实施 RAG 数据建设。

当前：

如果后端 RAG 未完成：

隐藏知识库菜单

DiagnosisResult：

rag_enabled = false

EvidencePanel：

显示“当前未启用外部医学知识库”

等后面正式开发：

数据源
Chunk
Embedding
Milvus
Rerank

以后再打开完整知识库功能。

==================================================
五十八、代码质量
==================================================

要求：

Vue Composition API

<script setup lang="ts">

严格 TypeScript

避免 any

API集中管理

组件职责明确

公共状态不滥用 Pinia

页面不出现大量重复 CSS

Element Plus 样式通过统一 Theme 覆盖

避免 !important 满天飞

ESLint

Prettier

不得留下影响功能的：

TODO

pass

mock placeholder

fake API

==================================================
五十九、实施顺序
==================================================

严格按下面顺序执行。

阶段1：

完整审查当前后端。

阶段2：

确认真实 API / Schema / 状态机。

阶段3：

只补前端真正需要的最小后端接口。

阶段4：

创建 Vue3 基础工程。

阶段5：

完成 Design System + MainLayout + Login。

阶段6：

患者列表 + 患者详情。

阶段7：

病例创建 + Case Workspace。

阶段8：

SSE实时 Graph 过程。

阶段9：

Doctor Review HITL。

阶段10：

Case List + Review Queue。

阶段11：

Checkpoint History + Time Travel。

阶段12：

Dashboard。

阶段13：

安全、异常、空状态、响应式。

阶段14：

Vitest + Playwright。

阶段15：

完整前后端联调。

==================================================
六十、最终必须真实联调
==================================================

禁止只启动：

npm run dev

看到页面就说完成。

必须真实验证：

Vue
→ FastAPI
→ MySQL

Vue
→ FastAPI
→ LangGraph
→ DeepAgent
→ MCP
→ MySQL

Vue
→ FastAPI
→ Cardiology SubGraph

Vue
→ FastAPI
→ Gastroenterology SubGraph

Vue
→ doctor_review interrupt

Vue
→ review API

FastAPI
→ Command resume

→ FINAL

Vue
→ history API
→ Checkpoint / Time Travel

全部链路真实走通。

==================================================
六十一、最终检查重点
==================================================

重点检查以下漏洞：

patient_id 越权

reviewer_id 前端伪造

AI_DRAFT 绕过 HITL

重复审核

两个医生并发审核

病例重复提交

SSE断连

LLM失败

MCP失败

登录失效

前端XSS

v-html

敏感数据console输出

Checkpoint原始数据泄露

API Key泄露

RAG未启用却伪造证据

Time Travel覆盖FINAL

==================================================
六十二、最终输出报告
==================================================

任务完成后必须输出：

1. 当前实际读取到的后端架构。

2. 后端原本存在的接口。

3. 为前端最小新增了哪些后端接口。

4. 是否修改 LangGraph / DeepAgent / MCP / SubGraph，为什么。

5. 前端最终目录。

6. 实现了哪些页面。

7. 实现了哪些公共组件。

8. 最终 API 契约。

9. SSE 如何实现。

10. HITL 如何实现。

11. Checkpoint / Time Travel 如何展示。

12. 审核版本冲突如何处理。

13. 最终测试结果。

14. npm build 是否成功。

15. 后端测试是否成功。

16. 前后端完整 DEMO 链路是否真实跑通。

17. 仍存在的明确问题。

禁止把未完成能力描述成已完成。

==================================================
六十三、最终原则
==================================================

前端不是单独项目。

必须严格服务当前 medical-multi-agent 后端架构。

最终产品体验应该是：

患者
→ 临床资料
→ AI综合分析
→ 专科Agent
→ 医学证据
→ 医生审核
→ 最终结果
→ 诊断复盘

技术关系保持：

Vue3 Clinical AI Workspace
        ↓
      FastAPI
        ↓
     LangGraph
        ↓
 ┌──────┼─────────┐
DeepAgent MCP   SubGraph
    │      │
    │    MySQL
    │
   RAG
    │
 Milvus
        ↓
Human-In-the-Loop
        ↓
      FINAL
        ↓
MySQL Checkpoint
        ↓
Time Travel

目标不是“能打开几个页面”。

目标是交付一个：

视觉专业、
交互完整、
与现有后端真实契合、
医生可以完整完成辅助诊断流程、
同时能体现 LangGraph 多智能体技术价值的企业级最小稳定前端 V1。
你现在负责对当前项目：

D:\workspace_py\medical-multi-agent

切换到 conda langchain_env312

实施 Medical Multi-Agent V1.2 企业级最小稳定版本。

这是一次真实代码实施任务，不是方案讨论，不是生成伪代码，不是只改前端页面。

======================================================================
一、最终目标
======================================================================

在当前 V1.1 医疗辅助多智能体基础上，完成：

1. 医生 Web：
   - 正式添加患者
   - 选择本次接诊科室
   - 填写主要主诉
   - 创建患者时同步创建第一次 MedicalVisit
   - 已存在患者可以新增一次 MedicalVisit
   - AI 病例必须能关联本次 Visit
   - 医生继续使用现有 AI DiagnosisGraph
   - 医生继续 Approve / Edit / Reject
   - FINAL / Checkpoint / History 继续保持

2. 微信小程序：
   - 独立 Consumer API
   - 独立 mini-program 前端目录
   - 微信登录
   - 本人健康档案
   - 家庭成员健康档案
   - 用户 AI 健康咨询
   - 动态 AI 预问诊
   - 每一轮消息先执行确定性 Risk Engine
   - AI 智能分诊
   - Redis Vector RAG
   - MedicalSupervisor
   - Cardiology / Gastroenterology SubAgent
   - Consumer Advice
   - 安全用药建议
   - 家庭成员协作咨询
   - 安全分享
   - 必要时转人工医生
   - 医生 Web 审核
   - 医生结果回流微信小程序

3. 基础架构：
   - 仍然只有一套核心业务数据库
   - 仍然共用一套 patients / medical records / medical_cases
   - Web 和小程序代码入口隔离
   - Doctor API 与 Consumer API 可独立运行和扩容
   - AI 长任务不能继续依赖 asyncio.create_task
   - 改为 Redis 持久任务队列 + 独立 AI Worker
   - 不增加 Kafka / RabbitMQ / RocketMQ
   - 不拆微服务
   - 不引入 Elasticsearch
   - 不恢复 Milvus
   - 正式 RAG 继续使用当前 Redis Vector Search

======================================================================
二、第一原则：先完整读取代码，再修改
======================================================================

禁止看到任务后直接开始新建大量文件。

必须先完整核查当前真实代码，包括但不限于：

app/main.py

app/api/
app/api/auth.py
app/api/patients.py
app/api/diagnosis.py
app/api/cases.py
app/api/review.py

app/services/
app/services/diagnosis_service.py
app/services/patient_access.py
app/services/health.py

app/persistence/
app/persistence/models.py
app/persistence/repositories.py
app/persistence/database.py
app/persistence/checkpoint.py

app/graph/
app/graph/workflow.py
app/graph/state.py
app/graph/nodes/*
app/graph/subgraphs/*

app/agents/
app/agents/medical.py
app/agents/cardiology.py
app/agents/gastroenterology.py

app/safety/risk.py

app/mcp/*
patient_mcp/*

app/rag/
app/rag/redis_store.py
app/rag/retriever.py
app/rag/embedding.py
app/rag/chunker.py
app/rag/document_loader.py

web/
web/src/components/patient/PatientCreateDialog.vue
web/src/views/patient/*
web/src/api/*
web/src/types/*
web/tests/*

tests/*

docker/docker-compose.yml
requirements.txt
pytest.ini
README.md

以及所有相关调用点和测试。

修改之前必须确认影响范围。

不得靠文件名猜逻辑。

======================================================================
三、当前代码基线，不允许误判
======================================================================

当前代码已经存在：

- FastAPI
- MySQL
- MySQL LangGraph Checkpoint
- DiagnosisService
- DiagnosisGraph
- MedicalSupervisor
- Cardiology SubGraph
- Gastroenterology SubGraph
- deterministic Risk Engine
- MCP
- Redis Vector Search RAG
- KnowledgeEvidence
- Doctor HITL
- Patient
- MedicalVisit
- MedicalCase
- MedicalAssessment
- KnowledgeDocument
- Vue Doctor Web

当前正式 RAG 已经改为 Redis Vector Search。

禁止重新恢复：

Milvus
etcd
MinIO

当前 app/api/diagnosis.py 使用：

asyncio.create_task(...)

启动 DiagnosisService.run_case()。

这个实现只能作为当前小规模实现，V1.2 必须移除这种长期 AI 任务调度方式。

======================================================================
四、架构边界必须定死
======================================================================

最终必须形成：

                    Shared Medical Core
                           |
             +-------------+-------------+
             |                           |
        Doctor API                   Consumer API
             |                           |
         Vue Web                    WeChat Mini
             |                           |
             +-------------+-------------+
                           |
                     Shared Services
                           |
         Patient / Risk / Agent / RAG / Diagnosis
                           |
                    MySQL + Redis

必须：

一套医疗数据库。
一套医疗核心能力。
两个独立业务入口。

绝对禁止：

doctor_patients
wechat_patients

doctor_medical_cases
wechat_medical_cases

MiniProgramDiagnosisService 复制 DiagnosisService

MiniProgramRagService 复制 RAG

MiniProgramPatientRepository 复制 PatientRepository

禁止为了小程序重新造第二套医疗核心。

======================================================================
五、医生 Web 与小程序代码必须解耦
======================================================================

Doctor Web：

web/

微信小程序：

mini-program/

必须完全独立。

web 不能 import mini-program。
mini-program 不能依赖 web 内部源码。

Backend：

现有 app/main.py 保留医生端兼容入口。

新增独立 Consumer ASGI 入口，例如：

app/consumer_main.py

Consumer API 放：

app/api/consumer/

例如：

app/api/consumer/auth.py
app/api/consumer/patients.py
app/api/consumer/consultations.py
app/api/consumer/sharing.py

Consumer API 禁止 import 医生 Controller。

Doctor 和 Consumer 只能共同依赖：

services
persistence
graph shared components
agents
rag
safety

保持现有医生 API 路径兼容。

不要为了“统一风格”大规模重命名现有：

/api/v1/patients
/api/v1/diagnoses
/api/v1/reviews

现有 Web 不允许因为 V1.2 发生大面积接口重写。

Consumer 独立使用：

/api/v1/consumer/*

======================================================================
六、正式补齐 Departments
======================================================================

当前 patients 不应该增加固定 department。

患者本身不是固定属于一个科室。

新增 departments 科室字典表。

最小字段：

pk_id
code
name
enabled
sort_order
created_at
updated_at

code 必须稳定唯一。

初始最少：

GENERAL
CARDIOLOGY
GASTROENTEROLOGY
NEUROLOGY
RESPIRATORY
ENDOCRINOLOGY

对应名称：

全科
心内科
消化内科
神经内科
呼吸内科
内分泌科

可以根据现有代码测试需求补充必要科室。

不要做：

复杂科室树
院区
楼层
床位
排班
号源

增加只读 API：

GET /api/v1/departments

医生添加患者时调用。

department 列表禁止在 Vue 中永久写死。

======================================================================
七、添加患者正式改造
======================================================================

当前 PatientCreateDialog 只有：

姓名
性别
出生日期
主要病史

正式修改为：

姓名 *
性别 *
出生日期
本次接诊科室 *
主要主诉 *
既往病史

本次接诊科室：

默认使用当前登录医生 department 对应的 department code。

允许医生切换。

前端必须：

- 从 departments API 获取科室
- loading
- error
- form validation
- 友好中文错误提示
- 创建成功自动进入患者详情

不得仅仅给 patients 添加 department。

======================================================================
八、患者创建必须同时建立第一次接诊
======================================================================

POST /api/v1/patients 请求增加：

department_code
chief_complaint

保留：

name
sex
birth_date
history

服务端必须完成：

BEGIN

INSERT patients

INSERT medical_visits

COMMIT

MedicalVisit 至少包含：

patient_id
visit_time
department
chief_complaint
record_json

如果需要稳定科室编码，可以在不破坏兼容性的前提下给 medical_visits 最小增加：

department_code nullable

保留现有 department 作为显示快照。

任何一步失败：

ROLLBACK。

不能出现：

Patient 创建成功
Visit 创建失败

这种半状态。

如果当前 PatientRepository.create() 内部自己 commit，
必须先分析影响范围，再以最小方式增加支持外部事务的能力。

禁止借机重构所有 Repository 事务模型。

======================================================================
九、已有患者新增接诊
======================================================================

增加：

POST /api/v1/patients/{patient_id}/visits

请求最少：

department_code
chief_complaint

创建：

MedicalVisit

患者详情页面增加：

[新增接诊]

不能每次来诊都重新创建 Patient。

======================================================================
十、MedicalCase 必须关联本次 Visit
======================================================================

当前：

Patient
  -> MedicalCase

V1.2 调整为：

Patient
  -> MedicalVisit
      -> MedicalCase

给 medical_cases 最小新增：

visit_id nullable
consultation_id nullable

均允许 null，保证旧数据兼容。

不要重复给 MedicalCase 存一份永久 department，
优先通过 visit_id 获取本次接诊科室。

Doctor 创建 AI Case 时：

必须明确关联当前 Visit。

如果患者存在多个 Visit，
不能随便选择第一条或最后一条而没有明确规则。

前端从具体 Visit 发起诊断时传 visit_id。

对现有旧调用保持兼容：
visit_id 可以暂时 nullable。

======================================================================
十一、科室与 Specialist Agent 严禁绑定死
======================================================================

禁止：

if department == "心内科":
    run cardiology

if department == "消化内科":
    run gastro

department 是业务接诊科室。

specialist_router 是 AI 临床推理路由。

必须继续保持：

患者症状
病史
检查
Risk
MedicalSupervisor
    ↓
specialist_router
    ↓
cardiology / gastroenterology / none

科室只作为上下文，不替代 AI specialist router。

======================================================================
十二、移除长期 asyncio.create_task 调度
======================================================================

当前 app/api/diagnosis.py 使用：

asyncio.create_task(
    DiagnosisService.run_case(...)
)

V1.2 必须改为：

API
 ↓
MySQL保存Case
 ↓
Redis Job Queue
 ↓
AI Worker
 ↓
DiagnosisService.run_case()
 ↓
LangGraph

使用适合当前 async Python 架构的轻量 Redis 队列。

优先：

ARQ

除非当前项目已经存在更合适且稳定的 Redis Queue 方案。

禁止增加：

Kafka
RabbitMQ
RocketMQ
Celery + RabbitMQ

如果选择 ARQ：

增加独立：

app/worker.py

或等价清晰入口。

任务最少：

run_doctor_case_job
run_consumer_analysis_job

API 和 AI Worker 必须可独立启动。

======================================================================
十三、AI Job 必须幂等
======================================================================

Worker 收到重复 case_id 时：

FINAL
REJECTED
WAITING_REVIEW

等不应该重复运行的状态不能再次执行完整 AI Graph。

必须校验当前 Case 状态。

任务失败：

写入明确失败状态。

不能：

无限 RUNNING。

至少保留：

failure_stage
error_code

如果现有 schema 最小增加字段即可。

禁止吞异常。

======================================================================
十四、Redis 使用原则
======================================================================

继续复用当前 Redis Stack。

用途按 Key Namespace 隔离：

medical:knowledge:chunk:*
    Redis Vector RAG
    不设 TTL

cache:*
    普通缓存
    必须 TTL

rate_limit:*
    限流
    TTL

job:*
    AI任务

ARQ 自己的 Key 使用独立前缀。

不能将 RAG Vector Key 设置 TTL。

不能启用会自动淘汰 RAG Key 的 allkeys-lru 之类策略。

Redis AOF 保持。

V1.2 第一版不增加第二套 Redis。

======================================================================
十五、Consumer 数据模型
======================================================================

所有表仍然放在同一 medical_ai 数据库。

新增：

1. consumer_users

最小：

pk_id
id            对外业务ID
openid        unique
unionid       nullable
nickname      nullable
avatar        nullable
status
created_at
updated_at

openid 不允许存到 patients。

2. consumer_patient_relations

最小：

id
consumer_user_id
patient_id
relation_type
permission
status
invited_by
created_at
updated_at

unique:

consumer_user_id + patient_id

relation_type：

self
father
mother
spouse
child
guardian
other

permission：

VIEW
CONTRIBUTE
MANAGE

3. consultations

最少：

pk_id
id
consumer_user_id
patient_id
thread_id
consultation_type
status
risk_level
recommended_department_code
linked_case_id nullable
failure_stage nullable
error_code nullable
source_channel
created_at
updated_at

source_channel 固定：

wechat_mini_program

4. consultation_messages

最少：

id
consultation_id
client_message_id
sender_type
sender_id
content_type
content
metadata_json nullable
created_at

必须唯一：

consultation_id + client_message_id

用于防微信网络重试造成消息重复处理。

sender_type：

PATIENT
FAMILY_MEMBER
AI
DOCTOR
SYSTEM

5. consultation_share_grants

最少：

id
consultation_id
created_by
share_token_hash
permission
expires_at
max_uses
used_count
status
created_at

数据库只能存 token hash。

不能永久存明文 share_token。

6. consumer_consent_records

最少：

id
consumer_user_id
agreement_type
agreement_version
consented_at
withdrawn_at

======================================================================
十六、不要增加第二套 Patient
======================================================================

微信用户第一次为自己创建健康档案：

ConsumerUser
    ↓
consumer_patient_relations
    ↓
Patient

Patient 继续写：

patients

source_channel：

wechat_mini_program

data_scope：

正式 Consumer 数据使用明确 real / consumer 对应策略，
不要继续伪装成 sandbox。

但是所有真实 Consumer 数据访问必须经过关系权限。

======================================================================
十七、患者自述与医生确认必须区分
======================================================================

小程序用户说：

“我有高血压”

不能自动变成：

“医生已确诊高血压”

至少在结构化数据中区分：

self_reported
clinician_confirmed
his_imported

可以在 summary_json 中最小演进：

self_reported_history
clinician_confirmed_history

或者建立清晰 source_type。

不要大规模新建复杂诊断表。

目标是让 Medical AI 明确知道：

患者自述
≠
医生确认
≠
HIS事实
≠
实验室检查

======================================================================
十八、微信登录
======================================================================

新增：

POST /api/v1/consumer/auth/wechat

请求：

微信 wx.login() 获得的 code

服务端：

code
 ↓
微信 code2Session
 ↓
openid / unionid
 ↓
创建或查询 consumer_user
 ↓
签发 Consumer Token

新增配置：

WECHAT_APP_ID
WECHAT_APP_SECRET
CONSUMER_AUTH_SECRET

Secret 只能从环境变量读取。

不能写进源码。

Consumer 鉴权必须和 Doctor 鉴权逻辑隔离。

Consumer 使用：

Authorization: Bearer <token>

或者当前架构中等价稳定实现。

不要让小程序复用医生 Cookie 登录。

======================================================================
十九、Consumer Patient Access
======================================================================

当前 PatientAccessService 只判断：

data_scope == sandbox

V1.2 必须拆出清晰访问策略。

例如：

DoctorPatientAccessService
ConsumerPatientAccessService

ConsumerPatientAccessService：

consumer_user
 ↓
consumer_patient_relations
 ↓
patient
 ↓
permission

没有合法 Relation：

禁止访问。

不能只靠 patient_id。

Doctor：

现有 sandbox 工作流继续。

对于微信转医生的真实 Patient，
医生必须只能通过合法病例/科室业务关系访问，
不能因此直接开放全库全部 Consumer Patient。

第一版可以按：

医生所属 department
+
MedicalCase.visit.department

判断其是否允许访问该 Consumer Patient 的本次接诊。

实现前必须检查现有医生工作台访问链。

======================================================================
二十、Consumer API
======================================================================

统一：

/api/v1/consumer/*

最少实现：

POST /api/v1/consumer/auth/wechat
GET  /api/v1/consumer/me

GET  /api/v1/consumer/patients
POST /api/v1/consumer/patients
PATCH /api/v1/consumer/patients/{patient_id}

POST /api/v1/consumer/consultations
GET  /api/v1/consumer/consultations
GET  /api/v1/consumer/consultations/{consultation_id}

GET  /api/v1/consumer/consultations/{id}/messages
POST /api/v1/consumer/consultations/{id}/messages

POST /api/v1/consumer/consultations/{id}/analyze

POST /api/v1/consumer/consultations/{id}/escalate

POST /api/v1/consumer/consultations/{id}/share
POST /api/v1/consumer/shares/{token}/redeem
DELETE /api/v1/consumer/shares/{grant_id}

消费者禁止访问：

/api/v1/reviews
/api/v1/dashboard

等医生内部接口。

======================================================================
二十一、Consultation 与 MedicalCase 严格分离
======================================================================

Consultation：

负责：

用户聊天
动态追问
家庭成员补充
AI预问诊
Consumer建议

MedicalCase：

负责：

正式多Agent医学辅助分析
医生审核
FINAL
病例审计

不能每发一条微信消息就创建 MedicalCase。

关系：

Consultation
     ↓
需要正式医学分析 / 转医生
     ↓
MedicalCase

======================================================================
二十二、Consultation 状态
======================================================================

最少：

CREATED
INTAKING
WAITING_USER
READY_ANALYSIS
ANALYZING
ADVICE_READY
ESCALATED
CLOSED
FAILED

状态变更必须服务端控制。

前端不能随意提交 status。

======================================================================
二十三、增加 ConsumerIntakeAgent
======================================================================

新增轻量：

app/agents/intake.py

职责严格限制为：

1. 从用户对话抽取结构化症状
2. 判断缺失的关键信息
3. 选择下一条最有价值的问题
4. 判断是否 ready_for_analysis

禁止负责：

最终疾病诊断
最终用药
处方
替代 MedicalSupervisor

Structured Output 最少：

chief_complaint
symptom_location
onset
duration
severity
character
associated_symptoms
medical_history
current_medications
allergies
pregnancy_status
vital_signs
missing_information
next_question
ready_for_analysis

不要每次固定问 30 个问题。

必须动态追问。

======================================================================
二十四、每条 Consumer Message 必须先执行 Risk Engine
======================================================================

流程必须是：

用户消息
 ↓
保存消息
 ↓
deterministic Risk Engine
 ↓
Emergency?
 ├─ YES
 │   ↓
 │ 立即生成紧急风险提示
 │ 不等待 LLM
 │ 不等待 RAG
 │ 不等待 MCP
 │
 └─ NO
     ↓
 Intake Agent

当前 app/safety/risk.py 必须复用并扩展测试。

关键要求：

即使：

LLM down
Redis Vector down
Embedding down
MCP down

Emergency 风险筛查仍然必须可运行。

======================================================================
二十五、Emergency 保护不能被 LLM 降级
======================================================================

已有：

deterministic risk == emergency
时
AI结果不能降级

必须保留。

增加 Consumer 路径相同保护。

至少测试：

压榨性胸痛 + 大汗
严重呼吸困难
一侧肢体无力 + 言语不清
严重过敏 + 呼吸困难
大量出血
意识不清

======================================================================
二十六、ConsumerConsultationGraph
======================================================================

不要修改医生当前 DiagnosisGraph 成为四不像。

新增：

app/graph/consumer/

例如：

consultation_graph.py

流程：

START
 ↓
normalize
 ↓
risk_screening
 ↓
emergency?
 ├─ yes
 │   ↓
 │ emergency_guidance
 │   ↓
 │ END
 │
 └─ no
     ↓
intake_extract
     ↓
information_complete?
 ├─ no
 │   ↓
 │ ask_next_question
 │   ↓
 │ WAITING_USER
 │
 └─ yes
     ↓
medical_analysis
     ↓
specialist_router
     ↓
cardiology / gastroenterology / none
     ↓
synthesis
     ↓
medication_safety
     ↓
consumer_advice
     ↓
END

每个 Consultation 使用：

thread_id = consultation.id

继续使用 MySQL LangGraph Checkpoint。

======================================================================
二十七、Medical Core 不允许复制
======================================================================

Consumer ConsultationGraph 应复用：

Risk Engine
MCP patient reads
Redis RAG
MedicalSupervisor核心能力
Cardiology
Gastroenterology
synthesis相关公共能力

不要复制：

medical_agent_v2.py
consumer_rag.py
mini_medical_agent.py

等几乎一模一样代码。

需要 audience 不同时：

抽公共 Medical Core Rule。

允许：

DoctorMedicalSupervisor
ConsumerMedicalSupervisor

但两者必须共用：

LLM配置
MCP读工具
RAG Tool
安全Middleware
Structured医疗结果
核心事实约束

主要区别只能是：

Audience Prompt
Output presentation

======================================================================
二十八、Consumer MCP 必须代码层只读
======================================================================

当前 patient MCP 已经存在：

create_patient
update_patient

Consumer Agent 禁止拿到这些工具。

Consumer MCP whitelist 只允许：

get_patient_summary
get_patient_visits
get_medical_records
get_lab_results
get_imaging_reports
get_medications
get_allergies

如果还有必要只读工具，可在分析后加入。

禁止仅依赖 Prompt：

“不要调用 create_patient”。

必须代码层过滤。

Consumer 写 Patient：

Consumer API
 ↓
Service
 ↓
Repository

不经过 Agent。

======================================================================
二十九、Redis RAG 继续正式使用
======================================================================

必须继续：

app/rag/redis_store.py
app/rag/retriever.py
app/rag/embedding.py

继续执行：

query
 ↓
embedding
 ↓
Redis Vector KNN
 ↓
score threshold
 ↓
KnowledgeEvidence

禁止：

Python本地自己算 cosine 替代 Redis Vector
Fake Evidence
LLM自己生成 document_id
LLM自己生成指南名称

RAG_REQUIRED=true 的真实分析：

Redis / Embedding / Knowledge 未就绪：

必须失败。

======================================================================
三十、AI智能分诊
======================================================================

Consumer 不要求用户先选择科室。

用户：

“我胸口疼”

AI预问诊完成以后输出：

recommended_department

但不能使用自由文本直接当业务编码。

增加：

DepartmentResolver

负责把：

心内科
心血管内科
心脏科

统一解析：

CARDIOLOGY

消化内科 / 胃肠科：

GASTROENTEROLOGY

无法可靠映射：

GENERAL

DepartmentResolver 需要确定性 mapping + 校验。

不要完全依赖 LLM 自由文本。

======================================================================
三十一、ConsumerAdvice 独立于医生 DiagnosisResult
======================================================================

当前 DiagnosisResult 是医生语言。

不能原样直接给普通用户。

新增 ConsumerAdvice Schema。

最少：

risk_level
urgency_message
summary
possible_directions
why_this_advice
what_to_do_now
recommended_department
recommended_department_code
recommended_tests
self_care
medication_guidance
red_flags
when_to_seek_emergency
missing_information
evidence
reliability_level
doctor_escalation_required

内部：

DiagnosisResult
 ↓
ConsumerAdviceAssembler
 ↓
ConsumerAdvice

不要修改医生端 DiagnosisResult 的含义。

======================================================================
三十二、Consumer 不直接显示疾病“百分比”
======================================================================

当前：

PossibleCondition.confidence

可以继续作为内部字段。

小程序禁止直接显示：

胃炎 87%
心肌梗死 73%

这种未经临床校准的疾病概率。

Consumer UI 显示：

较符合
需要排除
可能性有限

另显示：

建议可靠性：

较高
一般
有限

reliability_level 必须综合：

信息完整程度
RAG Evidence
Risk一致性
Specialist意见一致性
关键检查是否缺失

不得把 LLM confidence 原样当临床概率。

======================================================================
三十三、安全用药
======================================================================

新增：

MedicationSafetyGuard

不能让一个自由 Agent 直接给处方。

输入至少考虑：

年龄
性别
孕哺
药物过敏
当前用药
重要基础疾病
肝肾问题
RAG药品资料

输出：

ALLOW_SELF_CARE
ALLOW_OTC_INFORMATION
DOCTOR_REQUIRED
BLOCK_MEDICATION_GUIDANCE

三级原则：

A. 居家健康建议

允许。

B. OTC 非处方药信息

只有安全条件满足并有真实医学/药品 RAG Evidence 时允许提供受限说明。

C. 处方药

AI 不得形成正式处方。

提示：

需要医生进一步评估。

不得生成：

正式处方
医生签名
处方编号

======================================================================
三十四、家庭成员
======================================================================

一个 Consumer User 可以关联：

本人
父亲
母亲
配偶
子女
监护人

多个 Consumer User 也可以合法关联同一个 Patient。

例如：

儿子
女儿

共同管理父亲。

不要给 patients 增加：

owner_user_id

然后强制只能一个用户拥有。

家庭关系通过：

consumer_patient_relations

实现。

======================================================================
三十五、多人协作问诊
======================================================================

允许：

用户A：
“爸爸一直咳嗽”

AI：
“有没有发烧？”

患者本人B：
“昨晚38.5℃”

consultation_messages 必须记录：

sender_type
sender_id

AI上下文必须区分：

患者本人
家属
医生
系统
历史数据库

不能把家属说的话伪装成：

patient said

======================================================================
三十六、安全分享
======================================================================

实现 Consultation 分享。

不能：

?id=PT-10001
?consultation_id=123

直接作为访问授权。

必须生成高熵 share_token。

数据库只保存：

hash(token)

支持：

expires_at
max_uses
used_count
status

默认建议：

24小时
一次领取

领取后建立正式授权关系。

支持撤销。

撤销后立即失去访问权限。

分享一次 Consultation：

默认不能顺便读取患者所有历史病例。

最小权限原则。

======================================================================
三十七、Consumer 转医生
======================================================================

当：

风险较高
AI建议转医生
用户主动要求医生

调用：

POST /api/v1/consumer/consultations/{id}/escalate

事务：

BEGIN

创建 / 确认 MedicalVisit

department_code
=
AI DepartmentResolver 最终结果

department
=
科室显示快照

chief_complaint
=
Intake结构化主诉

创建 MedicalCase：

patient_id
visit_id
consultation_id
source_channel=wechat_mini_program

关联 Consultation

COMMIT

然后：

Redis Job
 ↓
DiagnosisGraph
 ↓
WAITING_REVIEW

医生 Web 能看到。

======================================================================
三十八、医生 Web 必须能识别 Consumer 来源
======================================================================

病例页面展示：

来源：

微信小程序 AI 预问诊

并展示：

患者主诉
结构化问诊摘要
患者本人/家属信息来源
Risk
AI初步建议
RAG Evidence
推荐科室

不能把 Consumer 数据隐藏成普通 doctor_web 病例。

======================================================================
三十九、医生结果回流
======================================================================

医生：

Approve
Edit
Reject

继续走当前 Doctor HITL。

最终：

MedicalAssessment
 ↓
Consultation linked_case_id
 ↓
Consumer API
 ↓
微信小程序

小程序必须明确展示：

AI初步建议

和：

医生最终意见

不能混成同一个结果。

医生结果优先级高于 AI 初步建议。

======================================================================
四十、微信小程序工程
======================================================================

新增：

mini-program/

优先使用：

微信原生小程序 + TypeScript

不要为了第一版引入大型跨端框架。

目录至少清晰包含：

pages/
services/
types/
stores或简单state/
utils/
components/

一级 Tab：

首页
咨询
记录
健康档案
我的

首页主入口：

哪里不舒服？

[开始AI健康咨询]

快捷入口：

症状咨询
检查结果解读
用药咨询
慢病咨询

第一版禁止增加：

商城
积分
社区
直播
会员
保险
医保
复杂支付

======================================================================
四十一、小程序咨询 UX
======================================================================

不能做成普通空白 ChatGPT。

用户：

“我头晕”

AI：

不要立即输出800字。

应该优先：

“我先确认几个重要信息，以便判断是否需要尽快就医。”

然后一个关键问题。

优先提供：

单选
多选
快捷按钮
文本补充

例如：

头晕更接近：

天旋地转
头昏发飘
站起来眼前发黑
走路不稳
说不清

可以显示：

信息完整度

不要叫：

诊断完成度。

======================================================================
四十二、AI身份
======================================================================

小程序显示：

AI健康助手

明确提示：

AI生成内容
不替代医生诊疗

不要包装：

AI主任医生
AI名医
AI专家医生

UI 可以像专业医疗问诊，
身份不能冒充真人医生。

======================================================================
四十三、流量控制
======================================================================

Consumer API 必须增加 Redis Rate Limit。

至少：

用户级
IP级
Consultation级
LLM调用频率
并发AI分析数

消息限制：

长度
频率

禁止一个用户无限刷模型。

限制参数必须配置化。

不要把数值散落代码。

======================================================================
四十四、文件/语音范围
======================================================================

V1.2 核心验收以：

文字 AI 问诊

为必须。

图片检查报告上传和语音输入：

可以预留结构与接口，
但如果没有真实识别能力，不允许做 Fake 按钮冒充完成。

不要因为缺少语音/图片能力阻断核心 V1.2。

======================================================================
四十五、健康检查
======================================================================

现有 Doctor：

/health

继续。

Consumer 增加适当健康状态接口，或共用内部 HealthService。

健康检查最少：

MySQL
Checkpoint
Redis
AI Job Queue
AI Worker
MCP
LLM
Embedding
Redis Vector
Knowledge Documents

必须区分：

configured
与
ready

例如：

RAG_ENABLED=true

不等于：

rag_ready=true

======================================================================
四十六、错误码
======================================================================

增加或规范：

MYSQL_UNAVAILABLE
REDIS_UNAVAILABLE
AI_QUEUE_UNAVAILABLE
AI_WORKER_UNAVAILABLE
MCP_UNAVAILABLE
LLM_UNAVAILABLE
EMBEDDING_UNAVAILABLE
REDIS_VECTOR_UNAVAILABLE
RAG_EMPTY
PATIENT_NOT_FOUND
PATIENT_ACCESS_DENIED
CONSULTATION_NOT_FOUND
CONSULTATION_ACCESS_DENIED
CONSULTATION_INVALID_STATE
DEPARTMENT_NOT_FOUND
SHARE_TOKEN_INVALID
SHARE_TOKEN_EXPIRED
RATE_LIMITED
AI_ANALYSIS_FAILED

对用户：

友好中文。

日志：

机器可定位 error_code。

======================================================================
四十七、日志与隐私
======================================================================

日志允许：

trace_id
case_id
consultation_id
thread_id
stage
error_code
duration_ms
rag_hit_count
model

禁止：

API Key
WECHAT_APP_SECRET
session_key
密码
完整医学对话
完整敏感患者信息
身份证
手机号

继续复用已有 PII redaction。

======================================================================
四十八、数据库迁移原则
======================================================================

不要借 V1.2 开始全面重构整个历史 Schema。

只修改本次明确需要的表。

优先遵循项目当前正在使用的 schema 初始化 / migration 机制。

如果项目已经正式启用 Alembic：

使用 Alembic。

如果当前运行仍然依赖 initialize_schema()：

本任务不要为了形式突然迁移整个历史数据库。

但新增 Schema 必须：

可重复执行
幂等
不能破坏历史数据
生产升级可控

======================================================================
四十九、禁止过度设计
======================================================================

V1.2 禁止：

Spring Cloud
微服务拆分
Kafka
RabbitMQ
RocketMQ
Kubernetes
Elasticsearch
GraphRAG
知识图谱
复杂Reranker
十几个SubAgent
第二套MySQL
第二套RAG
第二套Patient
第二套MedicalCase
复杂IAM
复杂医院组织树
支付
商城
预约挂号
处方配送

保持：

FastAPI
MySQL
Redis
LangGraph
DeepAgents
MCP
Vue
微信小程序

======================================================================
五十、测试：修改前先跑基线
======================================================================

修改代码前：

先执行当前能够执行的测试。

记录：

Python版本
Node版本
Docker状态
现有pytest结果
现有前端test/build/lint结果

如果测试本来已经失败：

必须记录 baseline failure。

不能以后把历史失败说成自己修改造成，
也不能隐藏。

======================================================================
五十一、L1 Unit Test
======================================================================

至少新增/补齐：

DepartmentResolver

PatientCreate schema

Patient + Visit输入校验

Risk Engine

ConsumerIntake structured result

ConsumerAdviceAssembler

MedicationSafetyGuard

ConsumerPatientAccessService

Share token

Share expiry

Share revoke

duplicate client_message_id

Consultation state transitions

AI Job idempotency

======================================================================
五十二、L2 MySQL Integration
======================================================================

真实 MySQL。

必须测试：

创建 Patient + Visit 成功

Visit失败时 Patient一起回滚

已有Patient新增Visit

MedicalCase关联visit_id

ConsumerUser

ConsumerPatientRelation

Consultation

Messages

重复client_message_id不重复插入

ShareGrant

Consent

Consumer越权访问失败

======================================================================
五十三、L3 Redis Integration
======================================================================

真实 Redis Stack。

必须测试：

PING

FT._LIST

Vector Index

真实 upsert

真实 KNN Search

正确 Top Result

delete_document

普通cache与Vector Key隔离

Rate Limit

AI Job Queue

Worker可以消费真实任务

======================================================================
五十四、L4 MCP + RAG + LLM Integration
======================================================================

禁止 Mock。

真实：

MCP HTTP
Embedding
Redis Vector
LLM

测试：

Patient
 ↓
MCP
 ↓
Medical Records

query
 ↓
Embedding
 ↓
Redis Vector
 ↓
KnowledgeEvidence

必须验证召回正确的指定知识文档。

不能只：

evidence.length > 0

还必须验证：

目标测试文档确实被召回。

负例 query：

不能返回明显伪相关 Evidence。

======================================================================
五十五、Doctor Real E2E
======================================================================

从零创建：

新 Patient

并同时创建：

Visit
Department
Chief Complaint

然后：

发起Diagnosis
 ↓
Redis Job
 ↓
AI Worker
 ↓
LangGraph
 ↓
MCP
 ↓
RAG
 ↓
Specialist
 ↓
WAITING_REVIEW
 ↓
Approve
 ↓
FINAL
 ↓
Checkpoint
 ↓
History

必须真实。

======================================================================
五十六、Consumer Real E2E
======================================================================

至少：

场景A：

创建Consumer
 ↓
创建本人Patient
 ↓
创建Consultation
 ↓
用户发送：
“右下腹越来越疼”
 ↓
AI追问
 ↓
用户继续补充
 ↓
Risk
 ↓
Intake ready
 ↓
真实LLM
 ↓
真实RAG
 ↓
Gastroenterology
 ↓
ConsumerAdvice

场景B Emergency：

用户：
“持续压榨性胸痛、大汗、呼吸困难”

必须：

Risk = emergency

且不依赖 LLM 成功才提示。

======================================================================
五十七、跨 Doctor + Consumer E2E
======================================================================

这是 V1.2 最重要验收。

必须：

Consumer创建Patient
 ↓
Consultation
 ↓
AI预问诊
 ↓
AI推荐CARDIOLOGY
 ↓
Consumer选择转医生
 ↓
创建MedicalVisit
 ↓
创建MedicalCase
 ↓
source_channel=wechat_mini_program
 ↓
Redis Job
 ↓
AI Worker
 ↓
WAITING_REVIEW
 ↓
Doctor Web / Doctor API可以看到
 ↓
医生Approve或Edit
 ↓
FINAL
 ↓
Consumer重新查询Consultation
 ↓
看到医生最终意见

这条链任何一段 Fake / Mock / 固定历史数据：

都不能算通过。

======================================================================
五十八、分享 E2E
======================================================================

用户A：

创建Consultation
 ↓
分享
 ↓
获得token
 ↓
用户B redeem
 ↓
可以查看被授权Consultation
 ↓
不能查看该Patient其他未分享病历
 ↓
用户A revoke
 ↓
用户B立即失去权限

测试：

过期token
重复token
超过max_uses
已撤销token

======================================================================
五十九、故障测试
======================================================================

至少验证：

Redis停止
AI Worker停止
MCP停止
错误Embedding配置
错误LLM配置
RAG Index缺失
Consumer越权Patient
Consultation错误状态
重复微信Message
Worker重复消费
Doctor并发审核409

必须：

明确FAILED / 503 / 409 / 对应错误。

禁止：

一直RUNNING
一直ANALYZING
静默降级
伪成功

======================================================================
六十、前端测试
======================================================================

Doctor Vue：

现有：

test
lint
build
Playwright

全部回归。

增加：

添加患者选择科室
主要主诉
Patient+Visit结果
新增接诊
从Visit发起AI诊断
Consumer来源病例展示

微信小程序：

至少建立：

typecheck
lint
unit tests

如果拥有真实微信 miniprogram-ci 凭据：

必须执行真实CI构建。

如果没有真实AppID/CI私钥：

不允许把该步骤写成PASS。

报告：

BLOCKED - missing real WeChat CI credential

不能：

SKIP == PASS。

======================================================================
六十一、真实微信登录验收
======================================================================

如果环境提供：

WECHAT_APP_ID
WECHAT_APP_SECRET

必须测试真实：

wx.login code
 ↓
服务端 code2Session
 ↓
openid
 ↓
consumer_user

如果没有：

实现必须完整，
普通单元测试可以隔离微信HTTP层，

但是最终验收报告必须写：

REAL_WECHAT_LOGIN = BLOCKED

不能说100%通过。

======================================================================
六十二、关键验收原则
======================================================================

只有：

FAIL = 0
ERROR = 0
Critical skipped = 0

并且真实外部依赖全部执行后，

才能写：

V1.2 REAL ACCEPTANCE PASS

以下任何一个缺失：

Real MySQL
Real Redis
Real Redis Vector
Real Job Worker
Real MCP
Real Embedding
Real LLM
Real Backend E2E
Doctor Live E2E
Consumer Critical E2E

禁止宣称：

100%真实测试通过。

======================================================================
六十三、最终必须输出 Acceptance Report
======================================================================

生成：

Medical Multi-Agent V1.2 Acceptance Report

至少：

Git Commit / 当前diff摘要

Python version
Node version

MySQL version
Redis version

LLM model
Embedding model

Redis Vector index
Knowledge document count
Knowledge chunk count

Doctor Backend Unit
Doctor Backend Integration

Consumer Unit
Consumer Integration

Redis Queue Integration

RAG Integration

Real LLM

Doctor Real Backend E2E

Consumer Real Backend E2E

Cross Channel E2E

Frontend Unit

Frontend Lint

Frontend Build

Doctor Playwright

Mini Program Typecheck
Mini Program Lint
Mini Program Tests
Mini Program Real Build（如有真实凭据）

Critical skipped

Blocked external acceptance

Failed

最终结论：

PASS
或
NOT READY

不得模糊处理。

======================================================================
六十四、实现顺序
======================================================================

严格按下面顺序执行，不要同时到处改：

Phase 0
完整代码审计
基线测试

Phase 1
Departments

Phase 2
添加患者：
Patient + Visit + Department + Chief Complaint

Phase 3
已有患者新增Visit
MedicalCase.visit_id

Phase 4
移除asyncio.create_task
Redis Job Queue + AI Worker

Phase 5
Consumer数据模型

Phase 6
Consumer Auth
Consumer Access Control

Phase 7
Consumer Consultation API

Phase 8
ConsumerIntakeAgent
每轮Risk

Phase 9
ConsumerConsultationGraph

Phase 10
Medical Core复用
Consumer MCP read-only
Redis RAG

Phase 11
DepartmentResolver
AI智能分诊

Phase 12
ConsumerAdvice
MedicationSafetyGuard

Phase 13
家庭成员
安全分享
多人协作咨询

Phase 14
Consumer → Doctor escalation

Phase 15
Doctor结果回流

Phase 16
微信小程序UI

Phase 17
测试补齐

Phase 18
真实Docker / MySQL / Redis / MCP / RAG / LLM / Worker E2E

Phase 19
Doctor + Consumer跨端E2E

Phase 20
验收报告

每个 Phase 完成后：

运行该阶段相关测试。

不要等全部改完才第一次测试。

======================================================================
六十五、必须保护现有功能
======================================================================

以下现有能力不得被破坏：

医生登录
患者列表
患者详情
Visits
Labs
Imaging
Medications
Allergies

AI辅助诊断

MedicalSupervisor
Cardiology
Gastroenterology

Risk

RAG

Knowledge API

WAITING_REVIEW

Approve
Edit
Reject

Assessment version optimistic lock

FINAL

MySQL Checkpoint

History

Time Travel read only

Doctor Vue

======================================================================
六十六、代码质量要求
======================================================================

必须：

类型明确
Pydantic Schema清晰
Service负责业务编排
Repository负责持久化
Controller保持薄
事务边界明确
外部网络调用不包长事务
错误码统一
日志可定位
敏感信息不入日志
关键操作幂等
跨用户访问有授权校验
避免循环依赖

禁止：

Controller里堆SQL

Agent直接SQL

MiniProgram直接访问数据库

MiniProgram直接访问MCP

Consumer直接访问Doctor Review API

硬编码科室列表散落多处

硬编码Secret

Fake RAG

Fake LLM

Fake MCP

======================================================================
六十七、最终产品定位
======================================================================

Doctor：

医疗辅助多智能体医生工作台

Consumer：

AI健康助手 / 智能预问诊

不要把Consumer包装成：

AI医生自动确诊
AI自动开处方

Consumer核心价值：

用户自然描述症状
 ↓
AI动态追问
 ↓
Risk
 ↓
医学知识RAG
 ↓
多智能体分析
 ↓
AI智能分诊
 ↓
可信的下一步健康建议
 ↓
必要时转医生
 ↓
医生最终审核

======================================================================
六十八、开始执行
======================================================================

现在开始。

第一步不是写代码。

第一步：

完整读取当前仓库实际实现，
输出简短的 Current State / Gap List，
确认哪些已经存在、哪些缺失、哪些与本任务冲突。

然后立即进入 Phase 0 和 Phase 1。

不要只给方案。

必须实际修改代码、运行测试、修复测试、继续推进。

除非遇到：

真实Secret缺失
真实微信凭据缺失
不可恢复外部依赖
破坏性数据库操作需要确认

否则不要因为小问题停止等待用户。

严禁提前宣称完成。

最终只有真实测试报告有资格决定是否 PASS。
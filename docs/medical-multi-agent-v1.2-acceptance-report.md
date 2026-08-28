# Medical Multi-Agent V1.2 Acceptance Report

验收日期：2026-08-28（Asia/Shanghai）

## 版本与运行环境

| 项目 | 结果 |
| --- | --- |
| 基线 Git Commit | `a66c84e` |
| Python | 3.12.13（conda `langchain_env312`） |
| Node.js | v24.12.0 |
| Docker Server | 29.6.2 |
| MySQL | 8.0.42，`medical-mysql` healthy |
| Redis Stack | image 7.4.0-v8 / Redis 7.4.7，`medical-redis` healthy，`noeviction` |
| LLM | `qwen3.5-omni-plus-2026-03-15` |
| Embedding | `text-embedding-v4`，1024 维 |
| Redis Vector | `medical_knowledge_v1`，HNSW / FLOAT32 / COSINE，索引存在 |
| 正式知识文档 | MySQL READY 文档 0，正式知识分片 0；存在 1 个未登记的历史 `test-bootstrap` 测试键 |

## 当前变更摘要

- 修复 BIGINT 主键迁移后按历史患者编号搜索不兼容的问题，病例/患者搜索同时支持别名和数值编号。
- 修复病例以 `CREATED/QUEUED` 状态进入 Web 页面时未连接 SSE、页面可能永久停在分析中的竞态。
- Consumer Advice 透传真实 RAG Evidence；跨端 E2E 使用唯一验收文档验证精确召回并自动清理。
- 健康检查分别报告 Redis、Vector Index、Embedding 与完整 RAG 就绪状态，服务版本更新为 V1.2。
- 移除 MySQL 科室种子语句中已弃用的 `VALUES()` 用法。
- Doctor Web 与微信小程序分别收敛为独立的 `service/site.json`、`service/config`、`service/http`；业务层只使用类型化 HTTP 方法，统一超时、鉴权、错误转换和环境配置。
- 更新真实 Playwright 用例，避免依赖已迁移的固定 UUID，并校验本次登录医生与审核人一致。

## 自动化与真实链路结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| Doctor Backend Unit + Integration | PASS | `pytest -q`: 51 passed，0 failed，0 skipped |
| Consumer Unit + Integration | PASS | 包含在 51 个 pytest；权限、分享、状态机、重复消息均通过 |
| Real MySQL | PASS | Patient + Visit 事务、Consumer 表、Checkpoint 等真实集成通过 |
| Real Redis / Queue / Worker | PASS | Redis Streams 消费、幂等与 Worker 心跳通过 |
| MCP + Real LLM | PASS | 真实 MCP HTTP 与真实 LLM 集成测试通过 |
| Real Embedding + Redis Vector | PASS | 唯一目标文档精确召回，负例不返回目标文档 |
| Doctor Real Backend E2E | PASS | Patient → Visit → Queue → Worker → Graph → Review → FINAL → History |
| Consumer Real Backend E2E | PASS | 消化科追问、急症确定性拦截、真实 AI Advice |
| Cross Channel E2E | PASS | Consumer → CARDIOLOGY → Visit/Case → Doctor Review → Consumer `CLOSED` |
| Consumer RAG Evidence | PASS | `document_id` 精确断言通过，验收向量结束后无残留 |
| Doctor Web Unit | PASS | Vitest 7/7 |
| Doctor Web Lint | PASS | ESLint 0 error |
| Doctor Web Build | PASS | Vue TypeScript + Vite production build |
| Doctor Playwright (Chromium headless) | PASS | 5/5；含真实登录、建档、诊断、审核、复盘与只读工作流 |
| Mini Program Typecheck | PASS | TypeScript 0 error |
| Mini Program Lint | PASS | ESLint 0 error |
| Mini Program Unit | PASS | Vitest 4/4 |
| Critical skipped（已执行门禁） | 0 | Playwright 使用 `LIVE_E2E=true` 与 `LIVE_FULL_E2E=true`，无跳过 |
| 最终自动化 Failed | 0 | 最终各门禁均通过 |

最近一次增强跨端 E2E 结果：

```json
{"consumer_user_id":"351711953216868352","patient_id":"351711953527246848","gastro_consultation_id":"351711953623715840","emergency_consultation_id":"351712039351095296","cross_channel_consultation_id":"351712039627919360","case_id":"351712120913530880","final_status":"CLOSED","doctor_result_returned":true}
```

## 阻塞的外部验收

| 项目 | 状态 | 原因 |
| --- | --- | --- |
| `REAL_WECHAT_LOGIN` | BLOCKED | 未提供真实 `WECHAT_APP_ID`、`WECHAT_APP_SECRET` 与一次性 `wx.login` code |
| Mini Program Real Build / Native UI Automation | BLOCKED | 未安装微信开发者工具，未提供真实 AppID 与 CI 私钥；不能用 Chromium 冒充微信运行时 |
| Production RAG Ready | BLOCKED | 仓库未提供已审核、可正式入库的医学知识源；当前 MySQL READY 文档数为 0，因此 `/health` 按设计返回 `degraded` |

## 最终结论

**NOT READY**

所有当前可执行的代码门禁与真实后端/无头浏览器/跨端链路均通过，但真实微信登录、微信原生构建以及正式医学知识内容尚未具备。按照任务验收规则，不能声明 `V1.2 REAL ACCEPTANCE PASS`，也不能声明“100% 真实测试通过”。

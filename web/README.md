# Clinical AI Workspace

Vue 3 医生临床工作台，所有业务请求均通过 Vite `/api` 代理访问 FastAPI。浏览器不会直接访问 MySQL、MCP、模型服务或 Checkpoint 数据库。

## 本地启动

```powershell
npm install
npm run dev
```

默认地址为 `http://127.0.0.1:5173`。本地 DEMO 登录账号为 `DEMO-D-001`，密码来自后端 `DEMO_LOGIN_PASSWORD` 环境变量。

## 验证

```powershell
npm run lint
npm test
npm run test:e2e
npm run build
```

`VITE_FEATURE_RAG=false` 时隐藏医学知识菜单，诊断工作台只显示“当前未启用外部医学知识库”，不会生成或展示虚假证据。

## 生产反向代理

Vue 构建产物位于 `dist/`。`/api/` 应代理至 FastAPI；SSE 路径必须关闭代理缓冲，例如 Nginx 使用 `proxy_http_version 1.1` 与 `proxy_buffering off`。

# H5 代理验收入口

原生小程序的 WXML/`wx.*` 运行时不能直接由 Chromium 执行，因此这里提供一个只用于验收的 H5 适配入口。它不复制业务逻辑，也不模拟 Consumer API；请求仍然使用 `mini-program/service/site.json` 中的 Consumer API host 和 `/api/v1/consumer/*` 路径。

## 登录参数约定

- 原生小程序：`wx.login()` 获取 `code`，调用 `POST /api/v1/consumer/auth/wechat`。
- H5 代理验收：登录页提交配置的 H5 验收账号和密码，调用 `POST /api/v1/consumer/auth/h5`；后端验证成功后创建/获取 Consumer 用户、签发 token 并把 token 摘要写入 Redis，浏览器仅把 token 放入当前会话的 `sessionStorage`。
- H5 也提供手工填写微信 `code` 的联调入口，仍然只调用同一个 `/auth/wechat`，不会在浏览器伪造 `wx.login()`。

## 启动

在 `mini-program/` 目录执行：

```bash
npm run h5:dev
```

访问 `http://127.0.0.1:5174/`。开发服务器会将 `/api/v1/consumer/*` 代理到 `service/site.json` 的 `dev.host`，因此不要求 Consumer API 额外开放 CORS。

## Playwright

先配置 H5 验收登录开关、账号密码，并确认 Consumer API 已启动；如果要覆盖转医生后的医生结果回流，还需要 AI Worker 与医生审核链路正常运行：

```powershell
$env:H5_CONSUMER_LOGIN_ENABLED = 'true'
$env:H5_CONSUMER_ACCOUNT = '<H5验收账号>'
$env:H5_CONSUMER_PASSWORD = '<H5验收密码>'
$env:H5_PROXY_E2E = 'true'
npm run h5:test:e2e
```

未配置 H5 验收账号时，Playwright 仍会运行入口标识 smoke test，业务链测试会明确报告为条件跳过。该入口和测试都标明 H5 代理验收，不替代微信开发者工具或真机验收。

`H5_CONSUMER_LOGIN_ENABLED` 默认关闭；生产环境不要开启验收账号登录，应使用正式的微信 H5 OAuth 方案。

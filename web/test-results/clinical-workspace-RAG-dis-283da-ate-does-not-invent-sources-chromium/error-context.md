# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: clinical-workspace.spec.ts >> RAG-disabled evidence state does not invent sources
- Location: tests\e2e\clinical-workspace.spec.ts:20:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('当前未启用外部医学知识库')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByText('当前未启用外部医学知识库')

```

```yaml
- complementary:
  - text: CA
  - strong: Clinical AI
  - text: 临床辅助工作台
  - navigation:
    - link "首页":
      - /url: /dashboard
    - link "患者中心":
      - /url: /patients
    - link "AI 辅助诊断":
      - /url: /cases
    - link "我的审核":
      - /url: /reviews
    - link "医学知识":
      - /url: /knowledge
    - link "个人中心":
      - /url: /profile
  - text: AI 仅提供辅助意见 最终结论须经医生审核
- button "切换侧边栏"
- button "部分服务异常"
- button "医生 DEMO 李医生 心内科 · 主治医师":
  - text: 医生
  - strong: DEMO 李医生
  - text: 心内科 · 主治医师
- main:
  - heading "医学知识" [level=1]
  - paragraph: 正式医学 RAG 知识库状态与文档版本
  - strong: 暂时无法加载
  - paragraph: 医学知识库状态加载失败
  - button "重新加载"
```

# Test source

```ts
  1  | import { expect, test } from '@playwright/test'
  2  | 
  3  | const doctor = { doctor_id: 'DEMO-D-001', name: 'DEMO 李医生', department: '心内科', title: '主治医师', role: 'doctor' }
  4  | 
  5  | test.beforeEach(async ({ page }) => {
  6  |   await page.route('**/api/v1/auth/me', async (route) => route.fulfill({ status: 401, json: { detail: '登录已失效' } }))
  7  |   await page.route('**/api/v1/auth/login', async (route) => route.fulfill({ json: { user: doctor } }))
  8  | })
  9  | 
  10 | test('doctor login restores the protected workspace', async ({ page }) => {
  11 |   await page.route('**/api/v1/dashboard/summary', async (route) => route.fulfill({ json: { today_cases: 3, pending_reviews: 1, high_risk_cases: 1, completed_cases: 2, trend: [], pending_items: [] } }))
  12 |   await page.goto('/login')
  13 |   await page.getByPlaceholder('请输入密码').fill('demo-clinical')
  14 |   await page.getByRole('button', { name: '登录工作台' }).click()
  15 |   await expect(page).toHaveURL(/dashboard/)
  16 |   await expect(page.getByText('我的待审核病例')).toBeVisible()
  17 |   await expect(page.getByText('AI 仅提供辅助意见')).toBeVisible()
  18 | })
  19 | 
  20 | test('RAG-disabled evidence state does not invent sources', async ({ page }) => {
  21 |   await page.route('**/api/v1/auth/me', async (route) => route.fulfill({ json: doctor }))
  22 |   await page.goto('/knowledge')
> 23 |   await expect(page.getByText('当前未启用外部医学知识库')).toBeVisible()
     |                                                ^ Error: expect(locator).toBeVisible() failed
  24 |   await expect(page.getByText('不会展示伪造证据')).toBeVisible()
  25 | })
  26 | 
  27 | test('desktop acceptance viewports have no page-level horizontal overflow', async ({ page }) => {
  28 |   await page.route('**/api/v1/auth/me', async (route) => route.fulfill({ json: doctor }))
  29 |   await page.route('**/api/v1/dashboard/summary', async (route) => route.fulfill({
  30 |     json: {
  31 |       today_cases: 8,
  32 |       pending_reviews: 3,
  33 |       high_risk_cases: 2,
  34 |       completed_cases: 5,
  35 |       trend: [
  36 |         { date: '2026-08-22', count: 2 },
  37 |         { date: '2026-08-23', count: 4 },
  38 |         { date: '2026-08-24', count: 3 },
  39 |         { date: '2026-08-25', count: 6 },
  40 |         { date: '2026-08-26', count: 4 },
  41 |         { date: '2026-08-27', count: 7 },
  42 |         { date: '2026-08-28', count: 8 },
  43 |       ],
  44 |       pending_items: [],
  45 |     },
  46 |   }))
  47 |   for (const viewport of [
  48 |     { width: 1440, height: 900 },
  49 |     { width: 1920, height: 1080 },
  50 |     { width: 2560, height: 1440 },
  51 |   ]) {
  52 |     await page.setViewportSize(viewport)
  53 |     await page.goto('/dashboard')
  54 |     await expect(page.getByText('近 7 日病例趋势')).toBeVisible()
  55 |     const dimensions = await page.evaluate(() => ({
  56 |       scrollWidth: document.documentElement.scrollWidth,
  57 |       clientWidth: document.documentElement.clientWidth,
  58 |     }))
  59 |     expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth)
  60 |   }
  61 | })
  62 | 
```
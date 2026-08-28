import { expect, test } from '@playwright/test'

const doctor = { doctor_id: 'DEMO-D-001', name: '李医生', department: '心内科', title: '主治医师', role: 'doctor' }

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/auth/me', async (route) => route.fulfill({ status: 401, json: { detail: '登录已失效' } }))
  await page.route('**/api/v1/auth/login', async (route) => route.fulfill({ json: { user: doctor } }))
})

test('doctor login restores the protected workspace', async ({ page }) => {
  await page.route('**/api/v1/dashboard/summary', async (route) => route.fulfill({ json: { today_cases: 3, pending_reviews: 1, high_risk_cases: 1, completed_cases: 2, trend: [], pending_items: [] } }))
  await page.goto('/login')
  await page.getByPlaceholder('请输入密码').fill('111111')
  await page.getByRole('button', { name: '登录工作台' }).click()
  await expect(page).toHaveURL(/dashboard/)
  await expect(page.getByText('我的待审核病例')).toBeVisible()
  await expect(page.getByText('AI 仅提供辅助意见')).toBeVisible()
})

test('RAG-disabled evidence state does not invent sources', async ({ page }) => {
  await page.route('**/api/v1/auth/me', async (route) => route.fulfill({ json: doctor }))
  await page.route('**/api/v1/knowledge/status', async (route) => route.fulfill({
    json: {
      rag_enabled: false,
      rag_required: false,
      rag_ready: false,
      redis: 'not configured',
      collection: 'medical_knowledge_v1',
      embedding_model: null,
      knowledge_documents: 0,
      message: '当前未启用外部医学知识库，不会展示伪造证据',
    },
  }))
  await page.route('**/api/v1/knowledge/documents**', async (route) => route.fulfill({
    json: { items: [], page: 1, page_size: 50, total: 0 },
  }))
  await page.goto('/knowledge')
  await expect(page.getByText('当前未启用外部医学知识库')).toBeVisible()
  await expect(page.getByText('不会展示伪造证据')).toBeVisible()
})

test('desktop acceptance viewports have no page-level horizontal overflow', async ({ page }) => {
  await page.route('**/api/v1/auth/me', async (route) => route.fulfill({ json: doctor }))
  await page.route('**/api/v1/dashboard/summary', async (route) => route.fulfill({
    json: {
      today_cases: 8,
      pending_reviews: 3,
      high_risk_cases: 2,
      completed_cases: 5,
      trend: [
        { date: '2026-08-22', count: 2 },
        { date: '2026-08-23', count: 4 },
        { date: '2026-08-24', count: 3 },
        { date: '2026-08-25', count: 6 },
        { date: '2026-08-26', count: 4 },
        { date: '2026-08-27', count: 7 },
        { date: '2026-08-28', count: 8 },
      ],
      pending_items: [],
    },
  }))
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
    { width: 2560, height: 1440 },
  ]) {
    await page.setViewportSize(viewport)
    await page.goto('/dashboard')
    await expect(page.getByText('近 7 日病例趋势')).toBeVisible()
    const dimensions = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth)
  }
})

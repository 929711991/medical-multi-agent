import { expect, test } from '@playwright/test'

test.skip(process.env.LIVE_E2E !== 'true', 'requires the local MySQL, MCP and FastAPI services')

test('real backend supports the doctor read workflow', async ({ page }) => {
  await page.goto('/login')
  await page.getByPlaceholder('请输入密码').fill('111111')
  await page.getByRole('button', { name: '登录工作台' }).click()
  await expect(page).toHaveURL(/dashboard/)
  await expect(page.getByText('我的待审核病例')).toBeVisible()

  const initialPatientsPromise = page.waitForResponse(
    (response) => response.request().method() === 'GET' && /\/api\/v1\/patients\?/.test(response.url()),
  )
  await page.getByRole('link', { name: '患者中心' }).click()
  expect((await initialPatientsPromise).status()).toBe(200)
  await page.getByPlaceholder('搜索患者姓名或编号').fill('PT-GASTRO')
  const patientResponsePromise = page.waitForResponse(
    (response) => response.request().method() === 'GET' && response.url().includes('/api/v1/patients?') && response.url().includes('search=PT-GASTRO'),
  )
  await page.getByRole('button', { name: '查询' }).click()
  const patientResponse = await patientResponsePromise
  expect(patientResponse.status()).toBe(200)
  const patients = (await patientResponse.json()) as { items: Array<{ patient_id: string; name: string }> }
  expect(patients.items).toHaveLength(1)
  const patient = patients.items[0]
  await expect(page.getByText('消化科患者 B')).toBeVisible()
  await page.getByRole('button', { name: '查看档案' }).click()
  await expect(page).toHaveURL(new RegExp(`/patients/${patient.patient_id}$`))
  await expect(page.getByRole('button', { name: '发起 AI 辅助诊断' })).toBeVisible()

  const caseResponsePromise = page.waitForResponse(
    (response) => response.request().method() === 'GET' && /\/api\/v1\/cases\?/.test(response.url()),
  )
  await page.getByRole('link', { name: 'AI 辅助诊断' }).click()
  const caseResponse = await caseResponsePromise
  expect(caseResponse.status()).toBe(200)
  const cases = (await caseResponse.json()) as { items: Array<{ id: string }> }
  expect(cases.items.length).toBeGreaterThan(0)
  const caseId = cases.items[0].id
  const caseRow = page.getByRole('row').filter({ hasText: caseId })
  await expect(caseRow).toBeVisible()
  await caseRow.getByRole('button', { name: '进入病例' }).click()
  await expect(page.getByText('临床摘要')).toBeVisible()
  await page.getByRole('link', { name: '诊断复盘' }).click()
  await expect(page.getByText('诊断执行轨迹')).toBeVisible()
  await expect(page.getByText('AI 原始意见与医生最终意见')).toBeVisible()
})

import { expect, test } from '@playwright/test'

test.skip(process.env.LIVE_FULL_E2E !== 'true', 'requires the local MySQL, MCP and FastAPI services')

test('doctor completes the flow from patient creation to final review', async ({ page }, testInfo) => {
  test.setTimeout(240_000)
  const suffix = Date.now().toString().slice(-8)
  const patientName = `全流程患者 ${suffix}`
  const question = '患者活动后出现胸痛并伴有出汗，有高血压病史，请进行风险筛查并给出鉴别诊断。'

  await page.goto('/login')
  await page.getByPlaceholder('请输入密码').fill('111111')
  await page.getByRole('button', { name: '登录工作台' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)

  await page.getByRole('link', { name: '患者中心' }).click()
  await expect(page.getByRole('heading', { name: '患者中心' })).toBeVisible()
  await page.getByRole('button', { name: /添加患者/ }).click()
  await page.getByPlaceholder('例如：张某').fill(patientName)
  await page.getByPlaceholder(/每行一条/).fill('高血压病史5年\n近期活动后胸痛')

  const patientResponsePromise = page.waitForResponse(
    (response) => response.request().method() === 'POST' && /\/api\/v1\/patients$/.test(response.url()),
  )
  await page.getByRole('button', { name: '保存并进入患者档案' }).click()
  const patientResponse = await patientResponsePromise
  expect(patientResponse.status()).toBe(201)
  const patient = (await patientResponse.json()) as { patient_id: string }
  await expect(page).toHaveURL(new RegExp(`/patients/${patient.patient_id}$`))
  await expect(page.getByText(patientName)).toBeVisible()

  await page.getByRole('button', { name: '发起 AI 辅助诊断' }).click()
  await page.getByPlaceholder(/患者活动后胸痛/).fill(question)
  const diagnosisResponsePromise = page.waitForResponse(
    (response) => response.request().method() === 'POST' && /\/api\/v1\/diagnoses$/.test(response.url()),
  )
  await page.getByRole('button', { name: '开始 AI 分析' }).click()
  const diagnosisResponse = await diagnosisResponsePromise
  expect(diagnosisResponse.status()).toBe(202)
  const diagnosis = (await diagnosisResponse.json()) as { case_id: string }
  await expect(page).toHaveURL(new RegExp(`/cases/${diagnosis.case_id}$`))

  await expect(page.getByText('AI 辅助意见 · 等待医生审核')).toBeVisible({ timeout: 180_000 })
  await expect(page.getByRole('heading', { name: '医学证据' })).toBeVisible()

  const reviewResponsePromise = page.waitForResponse(
    (response) => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/cases/${diagnosis.case_id}/review`),
  )
  await page.getByRole('button', { name: '审核通过' }).click()
  await page.getByRole('button', { name: '确认通过' }).click()
  const reviewResponse = await reviewResponsePromise
  expect(reviewResponse.status()).toBe(200)
  const reviewed = (await reviewResponse.json()) as { status: string; reviewer_id: string | null }
  expect(reviewed.status).toBe('FINAL')
  expect(reviewed.reviewer_id).toBe('DEMO-D-001')

  await page.getByRole('link', { name: '诊断复盘' }).click()
  await expect(page).toHaveURL(new RegExp(`/cases/${diagnosis.case_id}/history$`))
  await expect(page.getByRole('heading', { name: '诊断执行轨迹' })).toBeVisible()
  await expect(page.getByText('形成最终审核结果')).toBeVisible()
  await expect(page.getByText('AI 原始意见与医生最终意见')).toBeVisible()

  await testInfo.attach('final-clinical-flow', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})

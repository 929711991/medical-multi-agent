import { expect, test } from '@playwright/test'

test.skip(process.env.LIVE_E2E !== 'true', 'requires the local MySQL, MCP and FastAPI services')

test('real backend supports the doctor read workflow', async ({ page }) => {
  await page.goto('/login')
  await page.getByPlaceholder('请输入密码').fill('demo-clinical')
  await page.getByRole('button', { name: '登录工作台' }).click()
  await expect(page).toHaveURL(/dashboard/)
  await expect(page.getByText('我的待审核病例')).toBeVisible()

  await page.getByRole('link', { name: '患者中心' }).click()
  await page.getByPlaceholder('搜索患者姓名或编号').fill('DEMO-P-GASTRO')
  await page.getByRole('button', { name: '查询' }).click()
  await expect(page.getByText('DEMO 消化科患者 B')).toBeVisible()
  await page.getByRole('button', { name: '查看档案' }).click()
  await expect(page).toHaveURL(/patients\/DEMO-P-GASTRO/)
  await expect(page.getByRole('button', { name: '发起 AI 辅助诊断' })).toBeVisible()

  await page.getByRole('link', { name: 'AI 辅助诊断' }).click()
  await expect(page.getByText('cecfd34e-7cf5-4956-bb26-ecc2863d3e98')).toBeVisible()
  await page.getByRole('row', { name: /cecfd34e-7cf5-4956-bb26-ecc2863d3e98/ }).getByRole('button', { name: '进入病例' }).click()
  await expect(page.getByText('临床摘要')).toBeVisible()
  await page.getByRole('link', { name: '诊断复盘' }).click()
  await expect(page.getByText('诊断执行轨迹')).toBeVisible()
  await expect(page.getByText('AI 原始意见与医生最终意见')).toBeVisible()
})

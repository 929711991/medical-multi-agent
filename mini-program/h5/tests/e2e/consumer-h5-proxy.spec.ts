import { expect, test } from '@playwright/test'

test('shows an explicit H5 proxy acceptance entry before authentication', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('proxy-acceptance')).toContainText('H5 代理验收')
  await expect(page.getByRole('heading', { name: '登录', exact: true })).toBeVisible()
  await expect(page.getByText('小狐狸健康助手', { exact: true })).toBeVisible()
  await expect(page.getByTestId('h5-account')).toBeVisible()
  await expect(page.getByTestId('h5-password')).toBeVisible()
  await expect(page.getByText(/H5 账号登录仅用于验收，不替代微信开发者工具或真机验收/)).toBeVisible()
})

test.describe('Consumer API business-path acceptance through H5 proxy', () => {
  test.skip(
    process.env.H5_PROXY_E2E !== 'true'
      || !process.env.H5_CONSUMER_ACCOUNT
      || !process.env.H5_CONSUMER_PASSWORD,
    'requires a configured H5 acceptance account and a running Consumer API/worker; this is not a replacement for WeChat acceptance',
  )

  test('covers archive, consultation, deterministic risk, escalation and return query', async ({ page }) => {
    test.setTimeout(120_000)
    const account = process.env.H5_CONSUMER_ACCOUNT as string
    const password = process.env.H5_CONSUMER_PASSWORD as string
    const suffix = Date.now().toString().slice(-8)
    const patientName = `H5验收档案-${suffix}`

    await page.goto('/')
    await page.getByTestId('h5-account').fill(account)
    await page.getByTestId('h5-password').fill(password)
    await page.getByRole('button', { name: '登录小狐狸健康助手' }).click()
    await expect(page.getByTestId('proxy-badge')).toBeVisible()
    await expect(page.getByTestId('workspace-ready')).toBeAttached()

    await page.getByRole('button', { name: '健康档案', exact: true }).click()
    await page.getByLabel('姓名').fill(patientName)
    await page.getByLabel('患者自述病史').fill('自述有高血压史')
    await page.getByRole('button', { name: '新增档案' }).click()
    await expect(page.getByText(patientName)).toBeVisible()
    await expect(page.getByTestId('workspace-ready')).toBeAttached()

    await page.getByRole('button', { name: '健康咨询', exact: true }).click()
    await page.getByRole('button', { name: /创建.*咨询/ }).click()
    await expect(page.getByTestId('consultation-section')).toBeVisible()
    await expect(page.getByTestId('workspace-ready')).toBeAttached()
    await page.getByPlaceholder('请描述症状、持续时间和严重程度').fill('持续压榨性胸痛、大汗、呼吸困难')
    await page.getByRole('button', { name: '发送消息' }).click()
    await expect(page.getByTestId('risk-alert')).toContainText('请立即拨打 120')
    await page.getByRole('button', { name: '转人工医生审核' }).click()

    await expect(page.getByTestId('return-panel')).toBeVisible()
    await expect(page.getByTestId('return-panel')).toContainText('已转医生')
    await page.getByRole('button', { name: '刷新' }).click()
    await expect(page.getByTestId('return-panel')).toContainText('医生最终意见')
  })
})

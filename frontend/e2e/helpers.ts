import { expect, type Page } from '@playwright/test'

export async function loginThroughPage(page: Page, username: string, password: string): Promise<void> {
  await page.goto('/auth')
  await page.getByPlaceholder('输入用户名或邮箱').fill(username)
  await page.getByPlaceholder('至少 8 位，包含字母和数字').fill(password)
  await page.getByRole('button', { name: '登录并进入工作台' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

export async function registerAndLogin(page: Page, username: string, password: string): Promise<void> {
  await page.goto('/auth?mode=register')
  await page.getByPlaceholder('以字母开头，3–32 位').fill(username)
  await page.getByPlaceholder('name@example.com').fill(`${username}@example.com`)
  await page.getByPlaceholder('至少 8 位，包含字母和数字').fill(password)
  await page.getByPlaceholder('再次输入密码').fill(password)
  await page.getByText('我已阅读并同意用户协议与隐私说明', { exact: true }).click()
  await page.getByRole('button', { name: '注册账号', exact: true }).click()
  await expect(page.getByRole('button', { name: '登录并进入工作台' })).toBeVisible()
  await loginThroughPage(page, username, password)
}

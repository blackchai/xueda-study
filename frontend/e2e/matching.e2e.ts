import { randomBytes } from 'node:crypto'
import { expect, test, type BrowserContext } from '@playwright/test'
import { registerAndLogin } from './helpers.js'

const run = `match_${Date.now().toString(36)}`
const password = `Study9!${randomBytes(12).toString('hex')}`

function profile(name: string, isCpp = true) {
  return {
    name: `${name}_${run}`, school: 'E2E_PRIVATE_SCHOOL', major: 'E2E_PRIVATE_MAJOR', bio: 'E2E_PRIVATE_BIO',
    categories: [isCpp ? '编程开发' : '考研'], tags: [isCpp ? 'C++' : '考研英语'],
    styles: ['共同讨论'], stage: '强化', timezone: 'Asia/Shanghai',
    timeSlots: [{ day: 1, start: isCpp ? '19:00' : '08:00', end: isCpp ? '22:00' : '11:00' }],
    dailyTargetMinutes: 180, publicProfile: true,
  }
}

async function saveProfile(context: BrowserContext, payload: ReturnType<typeof profile>): Promise<void> {
  const response = await context.request.put('/api/v1/profiles/me', { data: payload })
  expect(response.status()).toBe(200)
}

test('三个真实浏览器会话：注册登录、档案保存、推荐更新、隐私和移动布局', async ({ browser }, testInfo) => {
  const baseURL = testInfo.project.use.baseURL!
  const sessions = await Promise.all([1, 2, 3].map(() =>
    browser.newContext({ baseURL, viewport: { width: 1440, height: 1000 } }),
  ))
  const [a, b, c] = sessions as [BrowserContext, BrowserContext, BrowserContext]
  const [pa, pb, pc] = await Promise.all(sessions.map((context) => context.newPage()))
  const pageErrors: string[] = []
  for (const page of [pa!, pb!, pc!]) page.on('pageerror', (error) => pageErrors.push(error.message))
  try {
    await registerAndLogin(pa!, `browser_a_${run}`, password)
    await registerAndLogin(pb!, `browser_b_${run}`, password)
    await registerAndLogin(pc!, `browser_c_${run}`, password)
    const bProfile = { ...profile('B'), timeSlots: [{ day: 1, start: '19:30', end: '22:30' }] }
    await saveProfile(a, profile('A'))
    await saveProfile(b, bProfile)
    await saveProfile(c, profile('C', false))

    // Actual Vue form save, rather than just calling the profile API.
    await pa!.goto('/profile')
    await expect(pa!.getByText(`A_${run}`, { exact: true }).first()).toBeVisible()
    await pa!.getByRole('button', { name: '编辑资料', exact: true }).click()
    await pa!.getByPlaceholder('建议使用昵称，不填写真实姓名').fill(`A已保存_${run}`)
    await pa!.getByRole('button', { name: '保存修改', exact: true }).click()
    await expect(pa!.getByRole('button', { name: '编辑资料', exact: true })).toBeVisible()
    await pa!.reload()
    await expect(pa!.getByPlaceholder('建议使用昵称，不填写真实姓名')).toHaveValue(`A已保存_${run}`)
    await expect(pa!.getByRole('switch', { name: '允许被推荐', exact: true })).toBeChecked()

    await pa!.goto('/buddies')
    await pa!.getByRole('textbox', { name: '搜索公开资料' }).fill(run)
    await pa!.getByRole('button', { name: '应用筛选', exact: true }).click()
    const cards = pa!.locator('.buddy-card')
    await expect(cards).toHaveCount(2)
    await expect(cards.nth(0)).toContainText(`B_${run}`)
    await expect(cards.nth(0).locator('.score-ring strong')).toHaveText('94')
    await expect(cards.nth(1).locator('.score-ring strong')).toHaveText('25')
    await expect(cards.nth(0).getByRole('button', { name: '对方未开启邀请' })).toBeDisabled()
    const publicData = await (await a.request.get(`/api/v1/buddies/recommendations?q=${run}`)).json()
    expect(JSON.stringify(publicData)).not.toMatch(/E2E_PRIVATE|@example.com|password|school|major|bio/)
    await pa!.screenshot({ path: testInfo.outputPath('buddies-desktop.png'), fullPage: true })
    await cards.nth(0).getByRole('button', { name: '查看匹配详情' }).click()
    await expect(pa!.getByText('每周学习计划 · 北京时间 UTC+8', { exact: true })).toBeVisible()
    await pa!.locator('.el-drawer__close-btn').click()

    // Update B's start and end via the real time selectors, then save.
    await pb!.goto('/profile')
    await pb!.getByRole('button', { name: '编辑资料', exact: true }).click()
    await pb!.locator('.time-slot-editor .el-select').nth(1).click()
    await pb!.getByRole('listbox', { name: '开始时间', exact: true }).getByRole('option', { name: '08:00', exact: true }).click()
    await pb!.locator('.time-slot-editor .el-select').nth(2).click()
    await pb!.getByRole('listbox', { name: '结束时间', exact: true }).getByRole('option', { name: '11:00', exact: true }).click()
    await pb!.getByRole('button', { name: '保存修改', exact: true }).click()
    await expect(pb!.getByRole('button', { name: '编辑资料', exact: true })).toBeVisible()
    await pa!.getByRole('button', { name: '刷新推荐', exact: true }).click()
    await expect(cards.nth(0).locator('.score-ring strong')).toHaveText('65')
    await pb!.getByRole('button', { name: '编辑资料', exact: true }).click()
    await pb!.getByRole('switch', { name: '允许被推荐', exact: true }).locator('..').locator('.el-switch__core').click()
    await pb!.getByRole('button', { name: '保存修改', exact: true }).click()
    await expect(pb!.getByRole('button', { name: '编辑资料', exact: true })).toBeVisible()
    await pa!.getByRole('button', { name: '刷新推荐', exact: true }).click()
    await expect(cards).toHaveCount(1)
    await expect(cards.first()).toContainText(`C_${run}`)

    await pa!.setViewportSize({ width: 390, height: 844 })
    await expect(cards.first()).toBeVisible()
    await expect(pa!.locator('.app-shell')).toHaveCSS('padding-left', '0px')
    await expect.poll(() => pa!.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await pa!.screenshot({ path: testInfo.outputPath('buddies-mobile.png'), fullPage: true })
    expect(await pa!.evaluate(() => localStorage.getItem('studymate.prototype.profile.v1'))).toBeNull()
    expect(await pa!.evaluate(() => localStorage.getItem('studymate.prototype.study.v1'))).toBeNull()

    const idA = (await (await a.request.get('/api/v1/auth/me')).json()).data.userId
    expect((await b.request.put(`/api/v1/profiles/${idA}`, { data: profile('越权') })).status()).toBe(404)
    const anonymous = await browser.newContext({ baseURL })
    expect((await anonymous.request.get('/api/v1/buddies/recommendations')).status()).toBe(401)
    await anonymous.close()
    expect(pageErrors).toEqual([])
  } finally {
    await Promise.all(sessions.map((context) => context.close()))
  }
})

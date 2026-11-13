import { randomBytes } from 'node:crypto'
import { expect, test, type Page } from '@playwright/test'
import { loginThroughPage, registerAndLogin } from './helpers.js'

const run = `buddy_${Date.now().toString(36)}`
const password = `Study9!${randomBytes(12).toString('hex')}`

function profile(name: string, allowInvites = true) {
  return {
    name: `${name}_${run}`, categories: ['编程开发'], tags: ['C++'], styles: ['共同讨论'], stage: '强化',
    timeSlots: [{ day: 1, start: '19:00', end: '22:00' }], timezone: 'Asia/Shanghai',
    school: 'PRIVATE_SCHOOL', major: 'PRIVATE_MAJOR', bio: 'PRIVATE_BIO',
    dailyTargetMinutes: 180, publicProfile: true, allowInvites,
  }
}

async function recommendations(page: Page) {
  await page.goto('/buddies')
  await page.getByRole('textbox', { name: '搜索公开资料' }).fill(run)
  await page.getByRole('button', { name: '应用筛选', exact: true }).click()
}

async function sendThroughPage(page: Page, name: string, message: string) {
  await recommendations(page)
  const card = page.locator('.buddy-card').filter({ hasText: `${name}_${run}` })
  await card.getByRole('button', { name: '申请成为搭子', exact: true }).click()
  await page.getByRole('textbox', { name: '邀请留言' }).fill(message)
  await page.getByRole('button', { name: '发送邀请', exact: true }).click()
  await expect(card.getByRole('button', { name: '等待接受', exact: true })).toBeDisabled()
}

test('真实搭子完整闭环：发送、通知已读、接受、拒绝、取消、重登、解除与越权拒绝', async ({ browser }, testInfo) => {
  const baseURL = testInfo.project.use.baseURL!
  const sessions = await Promise.all([1, 2, 3].map(() => browser.newContext({ baseURL, viewport: { width: 1440, height: 1000 } })))
  const [a, b, c] = sessions
  const [pa, pb, pc] = await Promise.all(sessions.map((context) => context.newPage()))
  if (!a || !b || !c || !pa || !pb || !pc) throw new Error('Missing browser contexts')
  const errors: string[] = []
  for (const page of [pa, pb, pc]) page.on('pageerror', (error) => errors.push(error.message))
  try {
    for (const [page, letter] of [[pa, 'a'], [pb, 'b'], [pc, 'c']] as const) {
      await registerAndLogin(page, `conn_${letter}_${run}`, password)
    }
    for (const [context, name, enabled] of [[a, 'A', true], [b, 'B', false], [c, 'C', true]] as const) {
      expect((await context.request.put('/api/v1/profiles/me', { data: profile(name, enabled) })).status()).toBe(200)
    }
    // B explicitly enables invitations in the real profile form, then refreshes.
    await pb.goto('/profile')
    await pb.getByRole('button', { name: '编辑资料', exact: true }).click()
    await pb.locator('.preference-list label').filter({ hasText: '接收搭子邀请' }).locator('.el-switch__core').click()
    await pb.getByRole('button', { name: '保存修改', exact: true }).click()
    await expect(pb.getByRole('button', { name: '编辑资料', exact: true })).toBeVisible()
    await pb.reload()
    await expect(pb.getByRole('switch', { name: '接收搭子邀请', exact: true })).toBeChecked()

    await sendThroughPage(pa, 'B', '周一一起学习 C++ 吧')
    await pa.getByRole('tab', { name: '已发送邀请', exact: true }).click()
    await expect(pa.locator('.connection-item')).toContainText('等待接受')
    const sent = (await (await a.request.get('/api/v1/buddy-requests?direction=outgoing')).json()).data.items[0]
    expect((await c.request.post(`/api/v1/buddy-requests/${sent.id}/accept`)).status()).toBe(404)
    expect((await c.request.post(`/api/v1/buddy-requests/${sent.id}/cancel`)).status()).toBe(404)
    // A repeated POST returns exactly the existing pending invitation.
    const repeated = await a.request.post('/api/v1/buddy-requests', { data: { recipientId: sent.recipientId, message: '重复点击' } })
    expect(repeated.status()).toBe(200)
    expect((await repeated.json()).data.id).toBe(sent.id)

    await pb.goto('/buddies')
    await pb.getByRole('button', { name: '站内通知', exact: true }).click()
    const receivedNotice = pb.locator('.connection-item').filter({ hasText: '收到搭子邀请' })
    await expect(receivedNotice).toContainText(`A_${run}`)
    await receivedNotice.getByRole('button', { name: '标为已读' }).click()
    await expect(receivedNotice.getByText('已读', { exact: true })).toBeVisible()
    await receivedNotice.getByRole('button', { name: '查看相关列表' }).click()
    const incomingA = pb.locator('.connection-item').filter({ hasText: `A_${run}` })
    await expect(incomingA).toContainText('周一一起学习 C++ 吧')
    await incomingA.getByRole('button', { name: '公开资料' }).click()
    await expect(pb.getByText('每周学习计划 · 北京时间 UTC+8', { exact: true })).toBeVisible()
    await pb.locator('.el-drawer:visible .el-drawer__close-btn').click()
    await incomingA.getByRole('button', { name: '接受邀请' }).click()
    await expect(incomingA).toContainText('已成为搭子')

    await pa.getByRole('tab', { name: '我的搭子', exact: true }).click()
    await expect(pa.locator('.connection-item')).toContainText(`B_${run}`)
    await pa.screenshot({ path: testInfo.outputPath('my-buddies-desktop.png'), fullPage: true })
    await pa.reload()
    await pa.getByRole('tab', { name: '我的搭子', exact: true }).click()
    await expect(pa.locator('.connection-item')).toContainText(`B_${run}`)
    const relation = (await (await a.request.get('/api/v1/buddies')).json()).data.items[0]
    expect((await c.request.delete(`/api/v1/buddies/${relation.id}`)).status()).toBe(404)

    await pb.goto('/profile')
    await pb.getByRole('button', { name: '退出登录', exact: true }).click()
    await expect(pb).toHaveURL(/\/auth$/)
    await loginThroughPage(pb, `conn_b_${run}`, password)
    await pb.goto('/buddies')
    await pb.getByRole('tab', { name: '我的搭子', exact: true }).click()
    await expect(pb.locator('.connection-item')).toContainText(`A_${run}`)
    const persistedNotices = (await (await b.request.get('/api/v1/notifications')).json()).data
    expect(persistedNotices.items[0].readAt).toBeTruthy()
    expect(JSON.stringify((await (await b.request.get('/api/v1/buddies')).json()).data)).not.toMatch(/PRIVATE_|@example.com|password|school|major|bio/)

    await recommendations(pa)
    await expect(pa.locator('.buddy-card').filter({ hasText: `B_${run}` }).getByRole('button', { name: '已成为搭子' })).toBeDisabled()
    await pa.getByRole('button', { name: '站内通知', exact: true }).click()
    await expect(pa.locator('.connection-item')).toContainText('搭子邀请已被接受')
    await pa.locator('.connection-item').getByRole('button', { name: '标为已读' }).click()

    await sendThroughPage(pc, 'B', '另一条申请用于拒绝测试')
    await pb.getByRole('tab', { name: '收到的邀请', exact: true }).click()
    const incomingC = pb.locator('.connection-item').filter({ hasText: `C_${run}` })
    await incomingC.getByRole('button', { name: '拒绝', exact: true }).click()
    await expect(incomingC).toContainText('已拒绝')
    await pc.getByRole('tab', { name: '已发送邀请', exact: true }).click()
    await expect(pc.locator('.connection-item')).toContainText('已拒绝')
    expect((await (await c.request.get('/api/v1/buddies')).json()).data.total).toBe(0)

    await sendThroughPage(pa, 'C', '这条申请将被取消')
    await pa.getByRole('tab', { name: '已发送邀请', exact: true }).click()
    const outgoingC = pa.locator('.connection-item').filter({ hasText: `C_${run}` })
    await outgoingC.getByRole('button', { name: '取消邀请' }).click()
    await expect(outgoingC).toContainText('已取消')

    await pb.getByRole('tab', { name: '我的搭子', exact: true }).click()
    await pb.locator('.connection-item').getByRole('button', { name: '解除关系' }).click()
    await pb.getByRole('button', { name: '确认解除', exact: true }).click()
    await expect(pb.getByText('暂无我的搭子', { exact: true })).toBeVisible()
    await pa.getByRole('button', { name: '站内通知', exact: true }).click()
    await expect(pa.locator('.connection-item').filter({ hasText: '搭子关系已解除' })).toContainText(`B_${run}`)
    await pa.screenshot({ path: testInfo.outputPath('buddy-notifications-desktop.png'), fullPage: true })
    await pa.setViewportSize({ width: 390, height: 844 })
    await expect(pa.locator('.app-shell')).toHaveCSS('padding-left', '0px')
    await expect.poll(() => pa.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await pa.screenshot({ path: testInfo.outputPath('buddy-notifications-mobile.png'), fullPage: true })
    expect(await pa.evaluate(() => localStorage.getItem('studymate.prototype.social.v1'))).toBeNull()
    expect((await (await a.request.get('/api/v1/buddies')).json()).data.total).toBe(0)
    expect((await b.request.post(`/api/v1/buddy-requests/${sent.id}/accept`)).status()).toBe(409)
    expect(errors).toEqual([])
  } finally {
    await Promise.all(sessions.map((context) => context.close()))
  }
})

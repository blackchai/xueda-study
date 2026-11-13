import { randomBytes } from 'node:crypto'
import { expect, test, type Page } from '@playwright/test'
import { loginThroughPage, registerAndLogin } from './helpers.js'

const run = `whole_${Date.now().toString(36)}`
const password = `Study9!${randomBytes(12).toString('hex')}`
async function center(page: Page): Promise<void> {
  await page.getByRole('button', { name: '打开通知中心', exact: true }).click()
  await expect(page).toHaveURL(/\/notifications$/)
  await expect(page.getByRole('heading', { name: '通知中心', exact: true })).toBeVisible()
}
async function share(page: Page, recordId: string, gid: string, content: boolean): Promise<void> {
  await page.goto('/checkins')
  await page.locator(`[data-checkin-id="${recordId}"]`).getByRole('button', { name: '分享到小组', exact: true }).click()
  const row = page.locator(`[data-share-group="${gid}"]`)
  if (content) await row.getByText('公开学习内容', { exact: true }).click()
  await row.getByRole('button', { name: '分享至本组', exact: true }).click()
  await expect(row.getByText('已分享', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '完成', exact: true }).click()
}

test('第六阶段全站：三个账号、目标任务、打卡、匹配邀请、小组、通知与网络异常', async ({ browser }, testInfo) => {
  test.setTimeout(120_000)
  const sessions = await Promise.all([1, 2, 3].map(() => browser.newContext({ baseURL: testInfo.project.use.baseURL!, timezoneId: 'Asia/Shanghai', viewport: { width: 1440, height: 1000 } })))
  const [a, b, c] = sessions
  const [pa, pb, pc] = await Promise.all(sessions.map(s => s.newPage()))
  if (!a || !b || !c || !pa || !pb || !pc) throw new Error('Missing browser contexts')
  const errors: string[] = []
  for (const p of [pa, pb, pc]) p.on('pageerror', e => errors.push(e.message))
  const recordIds: string[] = [], goalIds: string[] = [], userIds: string[] = []
  try {
    for (const [index, page] of [pa, pb, pc].entries()) {
      const letter = ['a', 'b', 'c'][index]!
      await registerAndLogin(page, `${run}_${letter}`, password)
      userIds.push((await (await page.request.get('/api/v1/auth/me')).json()).data.userId)
      // Each account uses the real goal create/edit and checkin Vue forms.
      await page.goto('/goals')
      await page.getByRole('button', { name: '创建目标', exact: true }).first().click()
      await page.getByPlaceholder('例如：计算机考研冲刺计划').fill(`${letter} 学习_${run}`)
      await page.getByRole('dialog').getByRole('button', { name: '创建目标', exact: true }).click()
      await expect(page.locator('.goal-card')).toHaveCount(1)
      await page.getByRole('button', { name: `管理目标：${letter} 学习_${run}`, exact: true }).click()
      await page.getByRole('menuitem', { name: '编辑目标', exact: true }).click()
      await page.getByPlaceholder('例如：计算机考研冲刺计划').fill(`${letter} 已修改_${run}`)
      await page.getByRole('button', { name: '保存修改', exact: true }).click()
      await expect(page.locator('.goal-card')).toContainText(`${letter} 已修改_${run}`)
      goalIds.push((await (await page.request.get('/api/v1/goals')).json()).data[0].id)
      if (index === 0) {
        await page.locator('.goal-card').getByRole('button', { name: '管理任务', exact: true }).click()
        await page.getByPlaceholder('任务名称', { exact: true }).fill('完成 C++ 第一章')
        await page.getByRole('button', { name: '添加', exact: true }).click()
        await page.locator('.managed-task-list .el-checkbox').click()
        await expect(page.locator('.managed-task-list input[type=checkbox]')).toBeChecked()
        await page.getByRole('button', { name: '完成', exact: true }).click()
        await expect(page.locator('.goal-progress')).toContainText('100%')
      }
      await page.goto('/checkins')
      await page.getByRole('button', { name: '记录今日学习', exact: true }).click()
      await page.getByPlaceholder('例如：完成数据结构二叉树章节，整理了 6 道错题……').fill(`${letter} 私人学习_${run}`)
      await page.getByRole('button', { name: '提交打卡', exact: true }).click()
      await expect(page.locator('.selected-records')).toContainText(`${letter} 私人学习_${run}`)
      recordIds.push((await (await page.request.get('/api/v1/checkins')).json()).data[0].id)
      await page.goto('/profile')
      await page.getByRole('button', { name: '退出登录', exact: true }).click()
      await expect(page).toHaveURL(/\/auth$/)
      expect((await page.request.get('/api/v1/goals')).status()).toBe(401)
      await loginThroughPage(page, `${run}_${letter}`, password)
      await page.goto('/goals')
      await expect(page.locator('.goal-card')).toContainText(`${letter} 已修改_${run}`)
      expect((await (await page.request.get('/api/v1/checkins')).json()).data[0].id).toBe(recordIds[index])
      expect((await page.request.put('/api/v1/profiles/me', { data: {
        name: `${letter.toUpperCase()}_${run}`, categories: [index === 2 ? '考研' : '编程开发'], tags: [index === 2 ? '考研英语' : 'C++'],
        styles: ['共同讨论'], stage: '强化', timeSlots: [{ day: 1, start: index === 2 ? '08:00' : '19:00', end: index === 2 ? '11:00' : '22:00' }],
        timezone: 'Asia/Shanghai', dailyTargetMinutes: 180, publicProfile: true, allowInvites: true,
        school: 'PRIVATE_SCHOOL', major: 'PRIVATE_MAJOR', bio: 'PRIVATE_BIO',
      } })).status()).toBe(200)
    }
    await pa.goto('/buddies')
    await pa.getByRole('textbox', { name: '搜索公开资料' }).fill(run)
    await pa.getByRole('button', { name: '应用筛选', exact: true }).click()
    const candidate = pa.locator('.buddy-card').filter({ hasText: `B_${run}` })
    await expect(candidate.locator('.score-ring strong')).toHaveText('100')
    await candidate.getByRole('button', { name: '申请成为搭子', exact: true }).click()
    await pa.getByRole('button', { name: '发送邀请', exact: true }).click()
    await expect(candidate.getByRole('button', { name: '等待接受', exact: true })).toBeDisabled()
    await center(pb)
    const invitation = pb.locator('.connection-item').filter({ hasText: '收到搭子邀请' })
    await expect(invitation).toHaveClass(/is-unread/)
    await invitation.getByRole('button', { name: '查看相关列表', exact: true }).click()
    await expect(pb).toHaveURL(/\/buddies\?tab=incoming$/)
    await pb.getByRole('button', { name: '接受邀请', exact: true }).click()
    await expect(pb.locator('.connection-item')).toContainText('已成为搭子')
    expect((await (await a.request.get('/api/v1/buddies')).json()).data.total).toBe(1)
    expect((await (await b.request.get('/api/v1/buddies')).json()).data.total).toBe(1)
    await center(pa)
    await pa.locator('.connection-item').filter({ hasText: '搭子邀请已被接受' }).getByRole('button', { name: '标为已读', exact: true }).click()

    await pa.goto('/groups')
    await pa.getByRole('button', { name: '创建小组', exact: true }).click()
    await pa.getByRole('textbox', { name: '小组名称', exact: true }).fill(`全站共学_${run}`)
    await pa.getByRole('textbox', { name: '小组介绍', exact: true }).fill('第六阶段完整业务流程')
    await pa.getByRole('button', { name: '确认创建', exact: true }).click()
    await expect(pa).toHaveURL(/\/groups\/[0-9a-f-]+$/)
    const gid = pa.url().split('/').pop()!
    await pb.goto(`/groups/${gid}`)
    await pb.getByRole('button', { name: '申请加入', exact: true }).click()
    await expect(pb.getByText('等待组长审核', { exact: true })).toBeVisible()
    await center(pa)
    const application = pa.locator('.connection-item').filter({ hasText: '收到小组加入申请' })
    await expect(application).toContainText(`B_${run}`)
    await application.getByRole('button', { name: '查看相关列表', exact: true }).click()
    await expect(pa).toHaveURL(new RegExp(`/groups/${gid}\\?tab=requests$`))
    await expect(pa.getByRole('tab', { name: '加入申请 · 1', exact: true })).toHaveAttribute('aria-selected', 'true')
    await pa.getByRole('button', { name: '同意', exact: true }).click()
    await expect(pa.getByRole('tab', { name: '加入申请 · 0', exact: true })).toBeVisible()
    await center(pb)
    await pb.locator('.connection-item').filter({ hasText: '小组申请已通过' }).getByRole('button', { name: '查看相关列表', exact: true }).click()
    await expect(pb.getByRole('tab', { name: '成员 · 2', exact: true })).toBeVisible()
    await share(pa, recordIds[0]!, gid, true)
    await share(pb, recordIds[1]!, gid, false)
    await pb.goto(`/groups/${gid}`)
    await expect(pb.getByTestId('today-members')).toHaveText('2')
    await expect(pb.getByTestId('total-minutes')).toHaveText('6 小时')
    await pb.getByRole('tab', { name: '学习排行榜', exact: true }).click()
    await expect(pb.locator('[data-rank-user]')).toHaveCount(2)
    const data = (await (await b.request.get(`/api/v1/groups/${gid}/rankings`)).json()).data
    expect(data.items.map((r: { minutes: number }) => r.minutes)).toEqual([180, 180])
    for (const path of [`/goals/${goalIds[0]}`, `/checkins/${recordIds[0]}`, `/groups/${gid}`, `/groups/${gid}/rankings`]) expect((await c.request.get('/api/v1' + path)).status()).toBe(404)
    expect((await c.request.delete(`/api/v1/goals/${goalIds[0]}`)).status()).toBe(404)
    expect((await c.request.delete(`/api/v1/checkins/${recordIds[1]}`)).status()).toBe(404)
    expect(JSON.stringify((await (await b.request.get(`/api/v1/groups/${gid}/checkins`)).json()).data)).not.toMatch(/b 私人|PRIVATE_|mood|goalId|email|password/)

    // A read-all does not approve a pending application.
    await pc.goto(`/groups/${gid}`)
    await pc.getByRole('button', { name: '申请加入', exact: true }).click()
    await expect(pc.getByText('等待组长审核', { exact: true })).toBeVisible()
    await center(pa)
    await pa.getByRole('button', { name: '全部标为已读', exact: true }).click()
    await expect(pa.getByRole('button', { name: '全部标为已读', exact: true })).toBeDisabled()
    expect((await c.request.get(`/api/v1/groups/${gid}`)).status()).toBe(404)
    await pa.locator('.connection-item').filter({ hasText: `C_${run}` }).getByRole('button', { name: '查看相关列表', exact: true }).click()
    await pa.getByRole('button', { name: '拒绝', exact: true }).click()
    await expect(pa.getByRole('tab', { name: '加入申请 · 0', exact: true })).toBeVisible()
    await center(pc)
    await expect(pc.locator('.connection-item')).toContainText('小组申请已被拒绝')
    const privateNotice = (await (await c.request.get('/api/v1/notifications')).json()).data.items[0]
    expect((await a.request.patch(`/api/v1/notifications/${privateNotice.id}/read`)).status()).toBe(404)

    await pa.getByRole('tab', { name: '成员 · 2', exact: true }).click()
    await pa.getByRole('button', { name: '移除成员', exact: true }).click()
    await pa.getByRole('button', { name: '确认', exact: true }).click()
    await expect(pa.getByRole('tab', { name: '成员 · 1', exact: true })).toBeVisible()
    await center(pb)
    await expect(pb.locator('.connection-item').filter({ hasText: '你已被移出学习小组' })).toBeVisible()
    expect((await b.request.get(`/api/v1/groups/${gid}/checkins`)).status()).toBe(404)
    await pb.reload()
    await expect(pb.locator('.connection-item').filter({ hasText: '你已被移出学习小组' })).toBeVisible()
    await expect(pb.locator('.app-main > .el-loading-mask')).toBeHidden()
    await pb.screenshot({ path: testInfo.outputPath('phase6-notifications-desktop.png'), fullPage: true, animations: 'disabled' })
    await pb.setViewportSize({ width: 390, height: 844 })
    await expect(pb.locator('.app-shell')).toHaveCSS('padding-left', '0px')
    await expect.poll(() => pb.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await pb.screenshot({ path: testInfo.outputPath('phase6-notifications-mobile.png'), fullPage: true, animations: 'disabled' })
    await pc.setViewportSize({ width: 390, height: 844 })
    await pc.goto('/groups')
    await pc.getByRole('button', { name: '创建小组', exact: true }).click()
    await pc.getByRole('textbox', { name: '小组名称', exact: true }).fill(`手机共学_${run}`)
    await pc.getByRole('textbox', { name: '小组介绍', exact: true }).fill('手机端真实表单验收')
    await expect.poll(() => pc.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await pc.screenshot({ path: testInfo.outputPath('phase6-mobile-form.png'), fullPage: false, animations: 'disabled' })
    await pc.getByRole('button', { name: '确认创建', exact: true }).click()
    await expect(pc).toHaveURL(/\/groups\/[0-9a-f-]+$/)
    await expect(pc.locator('.group-heading')).toContainText('手机端真实表单验收')

    // A real failed HTTP request must show an error and recover via retry.
    await pa.goto('/notifications')
    await pa.route('**/api/v1/notifications?*', route => route.abort('failed'))
    await pa.getByRole('button', { name: '刷新通知', exact: true }).click()
    await expect(pa.getByRole('alert')).toContainText('无法连接服务')
    await pa.unroute('**/api/v1/notifications?*')
    await pa.getByRole('button', { name: '重试', exact: true }).click()
    await expect(pa.locator('.connection-item')).not.toHaveCount(0)
    expect((await (await a.request.get(`/api/v1/groups/${gid}`)).json()).data.statistics.totalMinutes).toBe(180)
    expect((await (await b.request.get('/api/v1/goals')).json()).data[0].id).toBe(goalIds[1])
    expect((await (await b.request.get('/api/v1/checkins')).json()).data[0].id).toBe(recordIds[1])
    expect(errors).toEqual([])
    expect(await pa.evaluate(() => localStorage.getItem('studymate.prototype.social.v1'))).toBeNull()
  } finally { await Promise.all(sessions.map(s => s.close())) }
})

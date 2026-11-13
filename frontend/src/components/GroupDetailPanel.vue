<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import EmptyState from './EmptyState.vue'
import GroupFormFields from './GroupFormFields.vue'
import { groupsApi } from '@/services/groups'
import type { GroupDetail, GroupGoalWrite, GroupMember, GroupSummary, GroupWritePayload, JoinRequest, RankingPeriod, RankingResult, SharedCheckin } from '@/types/groups'

const props = defineProps<{ groupId: string; initialTab?: string }>()
const emit = defineEmits<{ closed: [] }>()
const preview = ref<GroupSummary | null>(null)
const detail = ref<GroupDetail | null>(null)
const members = ref<GroupMember[]>([])
const feed = ref<SharedCheckin[]>([])
const applications = ref<JoinRequest[]>([])
const ranks = ref<RankingResult | null>(null)
const feedTotal = ref(0), requestTotal = ref(0)
const feedPage = ref(1), requestPage = ref(1)
const period = ref<RankingPeriod>('week')
const tab = ref('feed')
const loading = ref(false), busy = ref(''), error = ref('')
const editOpen = ref(false), goalOpen = ref(false)
const editForm = ref<GroupWritePayload>({ name: '', category: '编程开发', description: '', tags: [], announcement: '', maxMembers: 30, requiresApproval: true })
const goalForm = ref<GroupGoalWrite>({ title: '', startDate: '', endDate: '', targetMinutes: 600 })
const owner = computed(() => preview.value?.myRole === 'owner')
let generation = 0
function clearPrivate(): void { detail.value = null; members.value = []; feed.value = []; applications.value = []; ranks.value = null; feedTotal.value = 0; requestTotal.value = 0 }
async function load(): Promise<void> {
  const run = ++generation, id = props.groupId
  loading.value = true; error.value = ''; clearPrivate()
  try {
    const summary = await groupsApi.preview(id)
    if (run !== generation) return
    preview.value = summary
    if (!summary.isJoined) return
    const [info, people, activity, ranking, requests] = await Promise.all([
      groupsApi.detail(id), groupsApi.members(id), groupsApi.feed(id, { page: feedPage.value }), groupsApi.rankings(id, period.value),
      summary.myRole === 'owner' ? groupsApi.requests(id, { page: requestPage.value }) : Promise.resolve(null),
    ])
    if (run !== generation) return
    if (feedPage.value > Math.max(1, Math.ceil(activity.total / 12))) { feedPage.value = Math.max(1, Math.ceil(activity.total / 12)); return }
    if (requestPage.value > Math.max(1, Math.ceil((requests?.total ?? 0) / 12))) { requestPage.value = Math.max(1, Math.ceil((requests?.total ?? 0) / 12)); return }
    detail.value = info; members.value = people.items; feed.value = activity.items; feedTotal.value = activity.total; ranks.value = ranking
    if (summary.myRole !== 'owner' && tab.value === 'requests') tab.value = 'feed'
    applications.value = requests?.items ?? []; requestTotal.value = requests?.total ?? 0
  } catch (e) { if (run === generation) { clearPrivate(); error.value = e instanceof Error ? e.message : '加载小组失败' } }
  finally { if (run === generation) loading.value = false }
}
watch([() => props.groupId, () => props.initialTab], () => { preview.value = null; tab.value = props.initialTab === 'requests' ? 'requests' : 'feed'; feedPage.value = 1; requestPage.value = 1; void load() }, { immediate: true })
watch([period, feedPage, requestPage], () => void load())
async function act(key: string, action: () => Promise<unknown>, message: string): Promise<void> {
  if (busy.value) return
  busy.value = key
  try { await action(); ElMessage.success(message); await load() }
  catch (e) { ElMessage.error(e instanceof Error ? e.message : '操作失败'); await load() }
  finally { busy.value = '' }
}
async function confirmAction(key: string, text: string, action: () => Promise<unknown>, success: string): Promise<void> {
  if (busy.value) return
  try { await ElMessageBox.confirm(text, '确认操作', { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }) } catch { return }
  await act(key, action, success)
}
function join(): void { void act('join', () => groupsApi.join(props.groupId), preview.value?.requiresApproval ? '申请已提交，等待组长审核' : '已加入小组') }
function cancel(): void {
  const req = preview.value?.joinRequest
  if (req?.status === 'pending') void act('cancel', () => groupsApi.resolve(props.groupId, req.id, 'cancel'), '已取消加入申请')
}
function leave(): void { void confirmAction('leave', '退出后，你在本组的分享会被撤回，个人打卡保留。确定退出吗？', () => groupsApi.leave(props.groupId), '已退出小组') }
function remove(m: GroupMember): void { void confirmAction('remove-' + m.userId, '移除「' + m.name + '」后，其在本组的分享会被撤回。', () => groupsApi.removeMember(props.groupId, m.userId), '成员已移除') }
function transfer(m: GroupMember): void { void confirmAction('transfer-' + m.userId, '将组长转让给「' + m.name + '」？你将成为普通成员。', () => groupsApi.transfer(props.groupId, m.userId), '组长已转让') }
async function dissolve(): Promise<void> {
  if (busy.value) return
  try { await ElMessageBox.confirm('解散后所有成员将失去本组访问权限，小组分享会撤回，个人打卡仍保留。此操作不能在页面撤销。', '解散小组', { type: 'warning', confirmButtonText: '确认解散', cancelButtonText: '取消' }) } catch { return }
  busy.value = 'dissolve'
  try { await groupsApi.dissolve(props.groupId); clearPrivate(); preview.value = null; ElMessage.success('小组已解散'); emit('closed') }
  catch (e) { ElMessage.error(e instanceof Error ? e.message : '解散失败') }
  finally { busy.value = '' }
}
function edit(): void {
  if (!detail.value) return
  const g = detail.value
  editForm.value = { name: g.name, category: g.category, description: g.description, tags: [...g.tags], announcement: g.announcement, maxMembers: g.maxMembers, requiresApproval: g.requiresApproval }
  editOpen.value = true
}
function saveEdit(): void {
  void act('edit', async () => { await groupsApi.update(props.groupId, editForm.value); editOpen.value = false }, '小组信息已更新')
}
function editGoal(): void {
  const g = detail.value
  if (!g) return
  goalForm.value = g.goal ? { title: g.goal.title, startDate: g.goal.startDate, endDate: g.goal.endDate, targetMinutes: g.goal.targetMinutes } : { title: '本周每人学习 C++ 至少 10 小时', startDate: g.statistics.weekStart, endDate: g.statistics.weekEnd, targetMinutes: 600 }
  goalOpen.value = true
}
function saveGoal(): void {
  void act('goal', async () => { await groupsApi.setGoal(props.groupId, goalForm.value); goalOpen.value = false }, '共同目标已保存')
}
const duration = (n: number): string => n >= 60 ? (Math.round(n / 60 * 10) / 10) + ' 小时' : n + ' 分钟'
const time = (s: string): string => new Date(s).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
</script>

<template>
  <div class="group-detail-panel" :aria-busy="loading">
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon><el-button text @click="load">重新加载</el-button></el-alert>
    <p v-if="loading" role="status">正在同步小组数据…</p>
    <template v-if="preview">
      <section class="group-heading surface-card">
        <div class="heading-copy"><span class="soft-tag">{{ preview.category }} · {{ preview.requiresApproval ? '审核加入' : '直接加入' }}</span><h2>{{ preview.name }}</h2><p>{{ preview.description }}</p><div class="tag-list"><span v-for="tag in preview.tags" :key="tag" class="soft-tag">{{ tag }}</span></div><small>组长 {{ preview.ownerName }} · {{ preview.memberCount }}/{{ preview.maxMembers }} 人</small></div>
        <div class="heading-actions"><el-button :icon="Refresh" :loading="loading" :disabled="!!busy" @click="load">刷新小组</el-button>
          <template v-if="!preview.isJoined"><el-button v-if="preview.joinRequest?.status === 'pending'" :loading="busy === 'cancel'" @click="cancel">取消加入申请</el-button><el-button v-else type="primary" :loading="busy === 'join'" :disabled="!!busy || preview.memberCount >= preview.maxMembers" @click="join">{{ preview.memberCount >= preview.maxMembers ? '人数已满' : preview.requiresApproval ? '申请加入' : '立即加入' }}</el-button></template>
          <template v-else-if="owner"><el-button :disabled="!!busy || !detail" @click="edit">编辑小组</el-button><el-button type="danger" plain :loading="busy === 'dissolve'" :disabled="!!busy" @click="dissolve">解散小组</el-button></template>
          <el-button v-else type="danger" plain :loading="busy === 'leave'" :disabled="!!busy" @click="leave">退出小组</el-button>
        </div>
      </section>
      <EmptyState v-if="!preview.isJoined && !loading" :title="preview.joinRequest?.status === 'pending' ? '等待组长审核' : '一起学习，从加入开始'" description="小组成员、公告、打卡动态和排行榜只向组员开放。" />
    </template>
    <template v-if="detail">
      <div v-if="detail.announcement" class="announcement"><strong>小组公告</strong><p>{{ detail.announcement }}</p></div>
      <section class="group-metrics" aria-label="小组学习统计">
        <div class="surface-card"><strong data-testid="today-members">{{ detail.statistics.todayMembers }}</strong><span>今日已打卡人数</span></div>
        <div class="surface-card"><strong data-testid="total-minutes">{{ duration(detail.statistics.totalMinutes) }}</strong><span>小组累计学习</span></div>
        <div class="surface-card"><strong>{{ duration(detail.statistics.weekMinutes) }}</strong><span>本周公开学习</span></div>
        <div class="surface-card"><strong>{{ detail.statistics.weekMembers }}</strong><span>本周参与人数</span></div>
      </section>
      <div class="detail-columns">
        <section class="surface-card detail-main">
          <el-tabs v-model="tab" aria-label="小组内容">
            <el-tab-pane label="打卡动态" name="feed">
              <p class="helper">只展示成员主动分享的记录。学习内容须单独授权；私人目标与心情始终不公开。</p>
              <router-link class="share-link" to="/checkins">去学习打卡，选择分享到本组 →</router-link>
              <article v-for="entry in feed" :key="entry.checkinId" class="feed-entry" :data-shared-checkin="entry.checkinId"><span class="avatar avatar--small">{{ entry.user.avatar }}</span><div><strong>{{ entry.user.name }}</strong><small>{{ entry.date }} · {{ entry.duration }} 分钟</small><p>{{ entry.content ?? '仅公开时长，学习内容未公开' }}</p></div></article>
              <EmptyState v-if="!feed.length" title="还没有公开打卡" description="先记录自己的学习，再主动选择分享。" />
              <el-pagination v-if="feedTotal > 12" v-model:current-page="feedPage" :total="feedTotal" :page-size="12" layout="prev, pager, next" />
            </el-tab-pane>
            <el-tab-pane label="学习排行榜" name="rankings">
              <el-radio-group v-model="period" aria-label="排行榜周期"><el-radio-button value="day">今日</el-radio-button><el-radio-button value="week">本周</el-radio-button><el-radio-button value="month">本月</el-radio-button><el-radio-button value="days">打卡天数</el-radio-button></el-radio-group>
              <p v-if="ranks" class="helper">{{ ranks.startDate }} 至 {{ ranks.endDate }} · 北京时间 UTC+8<br />{{ period === 'days' ? '按入组以来的公开打卡天数排序' : '按公开学习分钟数排序' }}；同分再比较天数、时长和用户 ID。未分享的成员记为 0。</p>
              <div class="rank-list"><article v-for="r in ranks?.items" :key="r.userId" :class="{ me: r.isMe }" :data-rank-user="r.userId"><b>{{ r.rank }}</b><span class="avatar avatar--small">{{ r.avatar }}</span><div><strong>{{ r.name }} {{ r.isMe ? '· 我' : '' }}</strong><small>{{ r.days }} 天 · {{ r.records }} 条公开记录</small></div><strong>{{ duration(r.minutes) }}</strong></article></div>
            </el-tab-pane>
            <el-tab-pane :label="'成员 · ' + members.length" name="members">
              <p v-if="owner" class="helper">组长须先转让给现有成员才能退出，也可以解散小组。移除成员将同时撤回其在本组的分享。</p>
              <article v-for="m in members" :key="m.userId" class="member-entry"><span class="avatar avatar--small">{{ m.avatar }}</span><div><strong>{{ m.name }} {{ m.isMe ? '· 我' : '' }}</strong><small>{{ m.role === 'owner' ? '组长' : '成员' }} · {{ time(m.joinedAt) }} 加入</small></div><div v-if="owner && !m.isMe" class="member-actions"><el-button size="small" :disabled="!!busy" @click="transfer(m)">转让组长</el-button><el-button size="small" type="danger" text :disabled="!!busy" @click="remove(m)">移除成员</el-button></div></article>
            </el-tab-pane>
            <el-tab-pane v-if="owner" :label="'加入申请 · ' + requestTotal" name="requests">
              <article v-for="req in applications" :key="req.id" class="member-entry"><div><strong>{{ req.name }}</strong><small>{{ time(req.createdAt) }} 申请加入</small></div><div class="member-actions"><el-button type="primary" :loading="busy === 'approve-' + req.id" :disabled="!!busy" @click="act('approve-' + req.id, () => groupsApi.resolve(props.groupId, req.id, 'approve'), '已同意加入')">同意</el-button><el-button :disabled="!!busy" @click="act('reject-' + req.id, () => groupsApi.resolve(props.groupId, req.id, 'reject'), '已拒绝申请')">拒绝</el-button></div></article>
              <EmptyState v-if="!applications.length" title="暂无待处理申请" description="新申请会在刷新后显示。" />
              <el-pagination v-if="requestTotal > 12" v-model:current-page="requestPage" :total="requestTotal" :page-size="12" layout="prev, pager, next" />
            </el-tab-pane>
          </el-tabs>
        </section>
        <aside class="detail-aside">
          <section class="surface-card goal-card"><div class="section-title"><h3>共同学习目标</h3><el-button v-if="owner" text type="primary" :disabled="!!busy" @click="editGoal">{{ detail.goal ? '修改目标' : '设置目标' }}</el-button></div>
            <template v-if="detail.goal"><h4>{{ detail.goal.title }}</h4><p>{{ detail.goal.startDate }} 至 {{ detail.goal.endDate }}</p><el-progress :percentage="detail.goal.progress" :stroke-width="9" /><strong data-testid="my-goal-progress">我已完成 {{ detail.goal.myMinutes }}/{{ detail.goal.targetMinutes }} 分钟</strong><p>当前周期内向本组分享的学习时长计入进度。目标内容由成员自律遵守。</p></template><p v-else>组长还没有设置共同目标。</p>
          </section>
          <section class="surface-card week-card"><h3>本周打卡足迹</h3><div v-for="day in detail.statistics.weekDays" :key="day.date"><time>{{ day.date.slice(5) }}</time><el-progress :percentage="Math.round(day.memberCount / detail.memberCount * 100)" :show-text="false" /><span>{{ day.memberCount }} 人</span></div><p class="helper">周一至周日，按不同成员去重。仅统计本次入组后主动分享的有效记录。</p></section>
        </aside>
      </div>
    </template>
    <el-dialog v-model="editOpen" title="编辑学习小组" width="600px" destroy-on-close :close-on-click-modal="!busy" :show-close="!busy"><GroupFormFields v-model="editForm" /><template #footer><el-button :disabled="!!busy" @click="editOpen = false">取消</el-button><el-button type="primary" :loading="busy === 'edit'" :disabled="!!busy" @click="saveEdit">保存小组</el-button></template></el-dialog>
    <el-dialog v-model="goalOpen" title="设置共同目标" width="500px" destroy-on-close :close-on-click-modal="!busy" :show-close="!busy"><div class="goal-form"><label>目标名称<el-input v-model="goalForm.title" aria-label="共同目标名称" maxlength="120" /></label><label>开始日期<el-date-picker v-model="goalForm.startDate" aria-label="目标开始日期" value-format="YYYY-MM-DD" :editable="false" /></label><label>截止日期<el-date-picker v-model="goalForm.endDate" aria-label="目标截止日期" value-format="YYYY-MM-DD" :editable="false" /></label><label>每人目标分钟数<el-input-number v-model="goalForm.targetMinutes" aria-label="目标分钟数" :min="1" :max="525600" :precision="0" /></label><p class="helper">周期最多 366 天；每人每天最多计入 1440 分钟。只有向本组分享的个人打卡参与统计。</p></div><template #footer><el-button :disabled="!!busy" @click="goalOpen = false">取消</el-button><el-button type="primary" :loading="busy === 'goal'" :disabled="!!busy" @click="saveGoal">保存目标</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.group-detail-panel { min-width: 0; }
.group-heading { display: flex; justify-content: space-between; padding: 26px; margin-bottom: 18px; gap: 24px; background: linear-gradient(130deg,#fff,#f2f2ff); }
.heading-copy { min-width: 0; overflow-wrap: anywhere; }
.heading-copy h2 { margin: 12px 0; font-size: 26px; }
.heading-copy p, .heading-copy small { color: var(--text-secondary); line-height: 1.7; white-space: pre-wrap; }
.heading-copy small { display: block; margin-top: 12px; }
.heading-actions { display: flex; align-content: flex-start; flex-wrap: wrap; gap: 8px; }
.heading-actions .el-button, .member-actions .el-button { margin-left: 0; }
.announcement { padding: 18px; margin-bottom: 18px; border-radius: 14px; background: var(--primary-soft); color: var(--primary-dark); overflow-wrap: anywhere; }
.announcement p { margin-bottom: 0; white-space: pre-wrap; }
.group-metrics { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 14px; margin-bottom: 18px; }
.group-metrics > div { padding: 20px; display: flex; flex-direction: column; gap: 9px; }
.group-metrics strong { font-size: 23px; color: var(--primary); }
.group-metrics span { font-size: 12px; color: var(--text-secondary); }
.detail-columns { display: grid; grid-template-columns: minmax(0,1.6fr) minmax(0,1fr); align-items: start; gap: 18px; }
.detail-main { padding: 22px; min-width: 0; }
.detail-aside { display: grid; gap: 18px; min-width: 0; }
.goal-card, .week-card { padding: 22px; overflow-wrap: anywhere; }
h3 { margin: 0 0 14px; font-size: 16px; }
.goal-card h4 { margin: 0; line-height: 1.7; }
.goal-card p, .helper { color: var(--text-secondary); font-size: 12px; line-height: 1.8; }
.goal-card > strong { display: block; margin-top: 12px; font-size: 13px; color: var(--primary); }
.goal-form { display: grid; gap: 14px; }
.goal-form label { display: grid; gap: 7px; }
.goal-form .el-date-editor { max-width: 100%; }
.week-card > div { display: grid; grid-template-columns: 45px 1fr 32px; align-items: center; gap: 8px; margin: 13px 0; font-size: 12px; }
.feed-entry, .member-entry, .rank-list article { display: flex; align-items: center; padding: 18px 0; gap: 12px; border-bottom: 1px solid var(--border-light); }
.feed-entry > div, .member-entry > div:first-of-type, .rank-list article > div { min-width: 0; flex: 1; }
.feed-entry strong, .member-entry strong, .rank-list strong { font-size: 13px; overflow-wrap: anywhere; }
.feed-entry p { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 13px; line-height: 1.8; }
.feed-entry small, .member-entry small, .rank-list small { display: block; margin-top: 5px; font-size: 11px; color: var(--text-muted); }
.share-link { color: var(--primary); font-size: 13px; }
.rank-list article { padding: 16px 8px; }
.rank-list article.me { background: var(--primary-soft); border-radius: 10px; }
.rank-list article > b { width: 20px; color: var(--primary); }
.rank-list article > strong { flex-shrink: 0; }
.member-actions { display: flex; flex-wrap: wrap; gap: 6px; }
.el-pagination { margin-top: 18px; max-width: 100%; }
@media(max-width:1100px) { .detail-columns { grid-template-columns: 1fr; } .detail-aside { grid-template-columns: repeat(2,minmax(0,1fr)); } }
@media(max-width:700px) { .group-heading { flex-direction: column; padding: 20px; } .group-metrics { grid-template-columns: repeat(2,minmax(0,1fr)); } .group-metrics > div { padding: 16px; } .group-metrics strong { font-size: 20px; } .detail-aside { grid-template-columns: 1fr; } .detail-main { padding: 14px; } .member-entry { flex-wrap: wrap; } .member-actions { width: 100%; } .rank-list article { gap: 7px; } .rank-list .avatar { display: none; } .detail-main :deep(.el-radio-button__inner) { padding: 8px 10px; } }
</style>

<script setup lang="ts">
import { Bell, Calendar as CalendarIcon, Check, Clock, Filter, InfoFilled, Refresh, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import BuddyConnections from '@/components/BuddyConnections.vue'
import PublicStudyProfile from '@/components/PublicStudyProfile.vue'
import { buddyConnectionsApi } from '@/services/buddyConnections'
import { matchingDataApi } from '@/services/matchingData'
import { useProfileStore } from '@/stores/profile'
import { useNotificationStore } from '@/stores/notifications'
import type { RecommendedBuddy, RecommendationFilters } from '@/types/matching'
import type { ConnectionTab } from '@/types/buddies'
import { GOAL_CATEGORIES, type DayOfWeek, type GoalCategory } from '@/types/models'

const router = useRouter()
const route = useRoute()
const notifications = useNotificationStore()
const profileStore = useProfileStore()
const category = ref<GoalCategory>()
const period = ref<RecommendationFilters['period']>()
const day = ref<DayOfWeek>()
const searchText = ref('')
const overlapOnly = ref(false)
const loading = ref(false)
const error = ref('')
const page = ref(1)
const pageSize = 12
const total = ref(0)
const buddies = ref<RecommendedBuddy[]>([])
const selectedBuddy = ref<RecommendedBuddy>()
const detailDrawerOpen = ref(false)
const activeTab = ref<'recommendations' | ConnectionTab>('recommendations')
const connectionTab = computed<ConnectionTab>(() => activeTab.value === 'recommendations' ? 'incoming' : activeTab.value)
const connectionsPanel = ref<InstanceType<typeof BuddyConnections>>()
const unreadCount = computed(() => notifications.unreadCount)
const notificationError = computed(() => notifications.error)
const inviteDialogOpen = ref(false)
const inviteTarget = ref<RecommendedBuddy>()
const inviteMessage = ref('你好！希望一起学习、定期交流计划。')
const sendingId = ref('')
let requestNumber = 0
const tabs = [
  { key: 'recommendations', title: '推荐搭子' }, { key: 'incoming', title: '收到的邀请' },
  { key: 'outgoing', title: '已发送邀请' }, { key: 'mine', title: '我的搭子' },
] as const

const dayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const completion = computed(() => Math.round([
  profileStore.profile.categories.length > 0, profileStore.profile.tags.length > 0,
  profileStore.profile.timeSlots.length > 0, profileStore.profile.styles.length > 0,
  Boolean(profileStore.profile.stage),
].filter(Boolean).length / 5 * 100))

async function loadPage(nextPage = 1): Promise<void> {
  const currentRequest = ++requestNumber
  loading.value = true
  error.value = ''
  buddies.value = []
  total.value = 0
  detailDrawerOpen.value = false
  page.value = nextPage
  if (!profileStore.apiMode) {
    loading.value = false
    return
  }
  try {
    const result = await matchingDataApi.getRecommendations({
      category: category.value, period: period.value, day: day.value,
      q: searchText.value.trim(), overlapOnly: overlapOnly.value,
      page: nextPage, pageSize,
    })
    if (currentRequest !== requestNumber) return
    buddies.value = result.items
    total.value = result.total
  } catch (cause) {
    if (currentRequest === requestNumber) error.value = cause instanceof Error ? cause.message : '推荐加载失败，请重试'
  } finally {
    if (currentRequest === requestNumber) loading.value = false
  }
}

async function refresh(): Promise<void> {
  try {
    await profileStore.initialize(true)
    await Promise.all([loadPage(1), refreshUnread(), connectionsPanel.value?.refresh()])
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '档案加载失败，请重试'
  }
}

async function refreshUnread(): Promise<void> {
  await notifications.refreshCount()
}

function inviteLabel(buddy: RecommendedBuddy): string {
  if (buddy.connection.status === 'connected') return '已成为搭子'
  if (buddy.connection.status === 'outgoing_pending') return '等待接受'
  return buddy.allowInvites ? '申请成为搭子' : '对方未开启邀请'
}

function openInvite(buddy: RecommendedBuddy): void {
  inviteTarget.value = buddy
  inviteMessage.value = '你好！希望一起学习、定期交流计划。'
  inviteDialogOpen.value = true
}

async function sendInvitation(): Promise<void> {
  if (!inviteTarget.value || sendingId.value) return
  sendingId.value = inviteTarget.value.id
  try {
    await buddyConnectionsApi.sendInvitation(inviteTarget.value.id, inviteMessage.value.trim())
    inviteDialogOpen.value = false
    ElMessage.success('邀请已提交，等待对方接受')
    await loadPage(page.value)
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '邀请发送失败，请稍后重试')
    await loadPage(page.value)
  } finally {
    sendingId.value = ''
  }
}

function connectionsChanged(): void {
  void refreshUnread()
  void loadPage(page.value)
}

function unreadChanged(count: number): void {
  notifications.acceptCount(count)
}

function clearFilters(): void {
  category.value = undefined
  period.value = undefined
  day.value = undefined
  searchText.value = ''
  overlapOnly.value = false
  void loadPage(1)
}

function scoreTone(score: number): string {
  if (score >= 85) return '高度匹配'
  if (score >= 70) return '较为合拍'
  return '可进一步了解'
}

function showDetails(buddy: RecommendedBuddy): void {
  selectedBuddy.value = buddy
  detailDrawerOpen.value = true
}

watch(activeTab, (tab) => { if (tab === 'recommendations') void loadPage(page.value) })
watch(() => route.query.tab, tab => {
  if (tab === 'incoming' || tab === 'outgoing' || tab === 'mine' || tab === 'notifications') activeTab.value = tab
}, { immediate: true })
onMounted(() => {
  void refresh()
})
onBeforeUnmount(() => { requestNumber += 1 })
</script>

<template>
  <div class="buddies-view">
    <PageHeader eyebrow="STUDY BUDDY" title="学习搭子" description="从真实学习档案中寻找同行者，每一个匹配分数都有清晰理由。">
      <template #actions>
        <el-button :icon="Setting" @click="router.push('/profile')">设置匹配偏好</el-button>
        <el-button :icon="Refresh" :loading="loading || profileStore.loading" @click="refresh">刷新推荐</el-button>
        <el-badge :value="unreadCount" :hidden="!unreadCount" :max="99">
          <el-button :icon="Bell" aria-label="站内通知" :disabled="!profileStore.apiMode" @click="activeTab = 'notifications'">通知</el-button>
        </el-badge>
      </template>
    </PageHeader>

    <el-alert v-if="!profileStore.apiMode" title="当前是 Mock 演示模式；真实搭子推荐需切换到 API 模式。" type="info" :closable="false" />
    <div class="matching-summary">
      <div class="matching-summary__copy">
        <span>你的匹配档案 · 北京时间 UTC+8</span>
        <strong>{{ profileStore.profile.categories.join(' · ') || '尚未设置学习方向' }}</strong>
        <p>{{ profileStore.profile.stage ?? '阶段未设置' }} · {{ profileStore.profile.styles.join('、') || '方式未设置' }}</p>
        <el-tag size="small" :type="profileStore.profile.publicProfile ? 'success' : 'info'">
          {{ profileStore.profile.publicProfile ? '已允许被推荐' : '尚未允许被推荐，仍可浏览他人' }}
        </el-tag>
      </div>
      <div class="profile-completion">
        <span>资料完整度</span><strong>{{ completion }}%</strong>
        <el-progress :percentage="completion" :show-text="false" :stroke-width="7" />
      </div>
      <div class="formula-summary"><span>S</span><p><strong>四维综合匹配</strong><small>目标 40% · 时间 35% · 方式 15% · 阶段 10%</small></p></div>
    </div>

    <nav class="buddy-tabs" role="tablist" aria-label="学习搭子功能">
      <button v-for="tab in tabs" :key="tab.key" type="button" role="tab" :aria-selected="activeTab === tab.key" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.title }}</button>
    </nav>
    <el-alert v-if="notificationError" :title="`通知同步失败：${notificationError}`" type="warning" :closable="false" />

    <section v-if="activeTab === 'recommendations'">

    <form class="buddy-filters surface-card" aria-label="筛选推荐搭子" @submit.prevent="loadPage(1)">
      <el-input v-model="searchText" placeholder="搜索公开昵称、方向或标签" aria-label="搜索公开资料" clearable maxlength="100" />
      <el-select v-model="category" placeholder="全部方向" aria-label="按学习方向筛选" clearable>
        <el-option v-for="item in GOAL_CATEGORIES" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="period" placeholder="全部时段" aria-label="按学习时段筛选" clearable>
        <el-option label="早晨 00:00–12:00" value="morning" />
        <el-option label="白天 12:00–18:00" value="daytime" />
        <el-option label="晚间 18:00–24:00" value="evening" />
      </el-select>
      <el-select v-model="day" placeholder="全部星期" aria-label="按星期筛选" clearable>
        <el-option v-for="(label, index) in dayNames" :key="label" :label="label" :value="index + 1" />
      </el-select>
      <el-checkbox v-model="overlapOnly">只看与我时间重合</el-checkbox>
      <div class="filter-actions">
        <el-button :icon="Filter" type="primary" native-type="submit" :loading="loading">应用筛选</el-button>
        <el-button @click="clearFilters">清除</el-button>
      </div>
    </form>

    <p class="result-note" role="status">共 {{ total }} 位推荐 · 仅展示主动开启匹配的用户 · 邀请和关系保存到服务端</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon>
      <template #default><el-button link type="primary" @click="refresh">重试加载</el-button></template>
    </el-alert>
    <el-skeleton v-else-if="loading || profileStore.loading" :rows="8" animated aria-label="正在加载推荐" />

    <section v-else-if="buddies.length" class="buddy-grid" aria-label="推荐搭子列表">
      <article v-for="buddy in buddies" :key="buddy.id" class="buddy-card surface-card surface-card--interactive">
        <div class="buddy-card__header">
          <span class="avatar">{{ buddy.avatar }}</span>
          <div><strong>{{ buddy.name }}</strong><span>{{ buddy.categories.join(' · ') || '方向未设置' }}</span></div>
          <div class="score-ring" :style="{ '--score-angle': `${buddy.score * 3.6}deg` }">
            <span><strong>{{ buddy.score }}</strong><small>匹配分</small></span>
          </div>
        </div>
        <span class="match-level">{{ scoreTone(buddy.score) }}</span>
        <p class="buddy-bio">{{ buddy.styles.join('、') || '学习方式未设置' }} · {{ buddy.stage ?? '阶段未设置' }}</p>
        <div class="tag-list"><span v-for="tag in buddy.tags" :key="tag" class="soft-tag">{{ tag }}</span></div>
        <div class="availability">
          <span v-for="(slot, index) in buddy.timeSlots.slice(0, 3)" :key="index"><CalendarIcon />{{ dayNames[slot.day - 1] }} {{ slot.start }}–{{ slot.end }}</span>
          <span v-if="!buddy.timeSlots.length">暂未设置可用时段</span>
          <small v-if="buddy.timeSlots.length > 3">另有 {{ buddy.timeSlots.length - 3 }} 个时段，可在详情查看</small>
          <strong><Clock /> 每周重合 {{ buddy.overlapMinutes }} 分钟</strong>
        </div>
        <div class="match-reasons">
          <strong><Check /> 推荐理由</strong>
          <span v-for="reason in buddy.reasons.slice(0, 3)" :key="reason">{{ reason }}</span>
          <small v-if="buddy.caveats[0]"><InfoFilled /> {{ buddy.caveats[0] }}</small>
        </div>
        <div class="buddy-actions">
          <el-button @click="showDetails(buddy)">查看匹配详情</el-button>
          <el-button v-if="buddy.connection.status === 'incoming_pending'" type="primary" @click="activeTab = 'incoming'">处理对方邀请</el-button>
          <el-button v-else type="primary" :disabled="!profileStore.apiMode || buddy.connection.status !== 'none' || !buddy.allowInvites || !!sendingId" :loading="sendingId === buddy.id" @click="openInvite(buddy)">{{ inviteLabel(buddy) }}</el-button>
        </div>
      </article>
    </section>
    <EmptyState v-else-if="!error" title="还没有符合条件的搭子" description="请完善自己的档案、放宽筛选，或请其他学习者开启“允许被推荐”。" symbol="⌕">
      <el-button @click="clearFilters">清除筛选</el-button>
      <el-button type="primary" @click="router.push('/profile')">完善学习档案</el-button>
    </EmptyState>

    <el-pagination v-if="total > pageSize" class="recommendation-pagination" :current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="loadPage" />
    </section>
    <BuddyConnections v-else-if="profileStore.apiMode" ref="connectionsPanel" :tab="connectionTab" @changed="connectionsChanged" @unread-change="unreadChanged" @navigate="activeTab = $event" />
    <el-alert v-else title="真实邀请、关系和通知仅在 API 模式可用。" type="info" :closable="false" />

    <el-dialog v-model="inviteDialogOpen" :title="`申请与 ${inviteTarget?.name ?? ''} 成为搭子`" width="min(94vw, 500px)" :close-on-click-modal="!sendingId" :close-on-press-escape="!sendingId" :show-close="!sendingId" destroy-on-close>
      <p class="invite-disclosure">发送后，对方可以查看你的昵称、学习方向、目标标签、方式、阶段和每周作息。邮箱和私人目标、打卡不会共享。</p>
      <el-input v-model="inviteMessage" type="textarea" :rows="3" maxlength="200" show-word-limit aria-label="邀请留言" placeholder="写一句你的共学期待（可选）" :disabled="!!sendingId" />
      <template #footer>
        <el-button :disabled="!!sendingId" @click="inviteDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="!!sendingId" @click="sendInvitation">发送邀请</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailDrawerOpen" :title="`${selectedBuddy?.name ?? ''} · 匹配详情`" size="min(92vw, 430px)">
      <div v-if="selectedBuddy" class="detail-content">
        <div class="detail-person"><span class="avatar">{{ selectedBuddy.avatar }}</span><div><strong>{{ selectedBuddy.name }}</strong><small>{{ selectedBuddy.categories.join(' · ') }}</small></div><b>{{ selectedBuddy.score }}<small>总分</small></b></div>
        <h3>四维得分</h3>
        <div class="dimension-list">
          <div><span>学习目标 G <small>40%</small></span><el-progress :percentage="selectedBuddy.dimensions.goal" /></div>
          <div><span>时间重合 T <small>35%</small></span><el-progress :percentage="selectedBuddy.dimensions.time" /></div>
          <div><span>学习方式 M <small>15%</small></span><el-progress :percentage="selectedBuddy.dimensions.method" /></div>
          <div><span>学习阶段 L <small>10%</small></span><el-progress :percentage="selectedBuddy.dimensions.level" /></div>
        </div>
        <PublicStudyProfile :profile="selectedBuddy" compact />
        <h3>为什么推荐</h3>
        <ul><li v-for="reason in selectedBuddy.reasons" :key="reason"><Check /> {{ reason }}</li></ul>
        <div v-if="selectedBuddy.caveats.length" class="caveat-box"><InfoFilled /><span>{{ selectedBuddy.caveats.join('；') }}</span></div>
        <p class="dialog-note">邮箱、学校、专业、个人简介、学习目标详情和打卡记录不属于公开推荐资料。</p>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.matching-summary { display: grid; align-items: center; padding: 22px 26px; margin-bottom: 20px; border: 1px solid #e2e3f7; border-radius: 18px; background: linear-gradient(135deg, #f7f7ff, #eef3ff); gap: 28px; grid-template-columns: 1.2fr 0.8fr 1fr; }
.matching-summary__copy { display: flex; flex-direction: column; }
.matching-summary__copy > span, .profile-completion > span { color: var(--text-muted); font-size: 9px; }
.matching-summary__copy strong { margin-top: 3px; font-size: 15px; }
.matching-summary__copy p { margin: 3px 0 0; color: var(--text-secondary); font-size: 9px; }
.profile-completion { display: grid; align-items: center; gap: 5px; grid-template-columns: 1fr auto; }
.profile-completion strong { color: var(--primary); font-size: 12px; }
.profile-completion :deep(.el-progress) { grid-column: 1 / -1; }
.formula-summary { display: flex; align-items: center; gap: 10px; }
.formula-summary > span { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 13px; color: #fff; background: var(--primary); font-family: Georgia, serif; font-size: 20px; font-style: italic; }
.formula-summary p { display: flex; margin: 0; flex-direction: column; }
.formula-summary strong { font-size: 11px; }
.formula-summary small { margin-top: 3px; color: var(--text-muted); font-size: 7px; }
.buddy-tabs { display: inline-flex; margin-bottom: 16px; border-bottom: 1px solid var(--border-light); }
.buddy-tabs button { position: relative; padding: 11px 19px; border: 0; color: var(--text-muted); background: transparent; cursor: pointer; font-weight: 750; }
.buddy-tabs button.active { color: var(--primary); }
.buddy-tabs button.active::after { position: absolute; right: 12px; bottom: -1px; left: 12px; height: 2px; border-radius: 2px; content: ''; background: var(--primary); }
.buddy-tabs button > span { display: inline-grid; width: 18px; height: 18px; margin-left: 4px; place-items: center; border-radius: 50%; color: #fff; background: var(--danger); font-size: 8px; }
.buddy-filters { display: grid; align-items: center; padding: 13px; margin-bottom: 17px; gap: 10px; grid-template-columns: minmax(200px, 1fr) 160px 140px auto; }
.search-field { position: relative; }
.search-field > svg { position: absolute; z-index: 2; top: 12px; left: 12px; width: 16px; color: var(--text-muted); }
.search-field :deep(.el-input__wrapper) { padding-left: 35px; }
.buddy-filters > span { display: inline-flex; align-items: center; color: var(--text-muted); font-size: 9px; gap: 5px; white-space: nowrap; }
.buddy-filters > span svg { width: 13px; }
.buddy-grid { display: grid; gap: 17px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.buddy-card { position: relative; padding: 21px; overflow: hidden; }
.buddy-card__header { display: flex; align-items: center; gap: 11px; }
.buddy-card__header > .avatar { position: relative; width: 48px; height: 48px; border-radius: 15px; }
.buddy-card__header > .avatar.online::after { position: absolute; right: -1px; bottom: -1px; width: 10px; height: 10px; border: 2px solid #fff; border-radius: 50%; content: ''; background: var(--success); }
.buddy-card__header > div:nth-child(2) { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.buddy-card__header div strong { font-size: 14px; }
.buddy-card__header div span { overflow: hidden; margin-top: 3px; color: var(--text-muted); font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
.score-ring { position: relative; display: grid; width: 56px; height: 56px; flex: 0 0 auto; place-items: center; border-radius: 50%; background: conic-gradient(var(--primary) var(--score-angle), #eceef6 0); }
.score-ring::after { position: absolute; width: 47px; height: 47px; border-radius: 50%; content: ''; background: #fff; }
.score-ring > span { z-index: 1; display: flex; align-items: center; flex-direction: column; }
.score-ring strong { color: var(--primary); font-size: 16px !important; line-height: 1; }
.score-ring small { margin-top: 2px; color: var(--text-muted); font-size: 6px; }
.match-level { display: inline-block; padding: 4px 8px; margin-top: 13px; border-radius: 999px; color: var(--primary); background: var(--primary-soft); font-size: 8px; font-weight: 750; }
.buddy-bio { min-height: 54px; margin: 10px 0 12px; color: var(--text-secondary); font-size: 10px; line-height: 1.75; }
.buddy-stats { display: grid; padding: 13px 0; margin-top: 15px; border-top: 1px solid var(--border-light); border-bottom: 1px solid var(--border-light); grid-template-columns: repeat(3, 1fr); }
.buddy-stats > span { display: flex; align-items: center; justify-content: center; border-right: 1px solid var(--border-light); flex-direction: column; }
.buddy-stats > span:last-child { border-right: 0; }
.buddy-stats svg { width: 13px; margin-bottom: 4px; color: var(--primary); }
.buddy-stats strong { font-size: 11px; }
.buddy-stats small { color: var(--text-muted); font-size: 7px; }
.match-reasons { display: flex; min-height: 106px; padding: 13px; margin: 14px 0; border-radius: 12px; background: #f7f8fc; gap: 5px; flex-direction: column; }
.match-reasons > strong { display: flex; align-items: center; margin-bottom: 3px; color: var(--text-strong); font-size: 9px; gap: 4px; }
.match-reasons strong svg { width: 12px; color: var(--success); }
.match-reasons > span { color: var(--text-secondary); font-size: 8px; }
.match-reasons > span::before { margin-right: 5px; color: var(--primary); content: '•'; }
.match-reasons > small { display: flex; align-items: flex-start; margin-top: 3px; color: #ad7a3f; font-size: 7px; gap: 4px; }
.match-reasons > small svg { width: 10px; flex: 0 0 auto; }
.buddy-actions { display: grid; gap: 8px; grid-template-columns: 0.8fr 1.2fr; }
.requests-panel { padding: 24px; }
.request-list article { display: flex; align-items: center; padding: 17px 4px; border-bottom: 1px solid var(--border-light); gap: 13px; }
.request-copy { min-width: 0; flex: 1; }
.request-copy > div { display: flex; align-items: center; gap: 7px; }
.request-copy p { margin: 6px 0; color: var(--text-secondary); font-size: 10px; line-height: 1.6; }
.request-copy small { color: var(--text-muted); font-size: 8px; }
.request-actions { display: flex; gap: 7px; }
.preference-form { display: flex; margin-top: 16px; gap: 8px; flex-direction: column; }
.preference-form > label { margin-top: 7px; color: var(--text-secondary); font-size: 10px; font-weight: 750; }
.preference-form :deep(.el-select) { width: 100%; }
.option-grid { display: grid; gap: 7px; grid-template-columns: repeat(3, 1fr); }
.option-grid :deep(.el-checkbox) { margin-right: 0; }
.weekday-grid { display: flex; flex-wrap: wrap; }
.invite-summary { display: flex; align-items: center; padding: 13px; margin-bottom: 14px; border-radius: 12px; background: #f5f6fb; gap: 10px; }
.invite-summary > div { display: flex; flex-direction: column; }
.invite-summary small { margin-top: 3px; color: var(--text-muted); font-size: 8px; }
.dialog-note { margin: 9px 0 0; color: var(--text-muted); font-size: 8px; }
.detail-content > p { color: var(--text-secondary); font-size: 11px; line-height: 1.7; }
.detail-person { display: flex; align-items: center; gap: 11px; }
.detail-person > div { display: flex; flex: 1; flex-direction: column; }
.detail-person div small { color: var(--text-muted); font-size: 9px; }
.detail-person > b { color: var(--primary); font-size: 24px; }
.detail-person > b small { display: block; color: var(--text-muted); font-size: 7px; text-align: center; }
.detail-content h3 { margin: 24px 0 12px; font-size: 13px; }
.dimension-list { display: flex; gap: 14px; flex-direction: column; }
.dimension-list > div > span { display: flex; justify-content: space-between; margin-bottom: 6px; color: var(--text-secondary); font-size: 9px; }
.dimension-list span small { color: var(--text-muted); }
.detail-content ul { padding: 0; list-style: none; }
.detail-content li { display: flex; align-items: center; margin-top: 9px; color: var(--text-secondary); font-size: 10px; gap: 7px; }
.detail-content li svg { width: 13px; color: var(--success); }
.caveat-box { display: flex; padding: 12px; margin-top: 18px; border-radius: 11px; color: #8f653c; background: #fff6ea; font-size: 9px; line-height: 1.6; gap: 7px; }
.caveat-box svg { width: 14px; flex: 0 0 auto; }
.drawer-action { width: 100%; margin-top: 22px; }

@media (max-width: 1200px) { .buddy-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 760px) {
  .matching-summary { grid-template-columns: 1fr; gap: 18px; }
  .formula-summary { display: none; }
  .buddy-filters { grid-template-columns: 1fr 1fr; }
  .search-field { grid-column: 1 / -1; }
  .buddy-filters > span { grid-column: 1 / -1; }
  .buddy-grid { grid-template-columns: 1fr; }
  .request-list article { align-items: flex-start; flex-wrap: wrap; }
  .request-copy { min-width: calc(100% - 64px); }
  .request-actions { width: 100%; padding-left: 57px; }
  .option-grid { grid-template-columns: repeat(2, 1fr); }
}

.availability { display: flex; flex-direction: column; gap: 6px; margin-top: 14px; color: var(--text-secondary); font-size: 11px; }
.availability span, .availability strong { display: flex; align-items: center; gap: 5px; }
.availability svg { width: 13px; }
.availability small { color: var(--text-muted); }
.result-note { color: var(--text-muted); font-size: 11px; line-height: 1.8; }
.filter-actions { display: flex; gap: 8px; }
.buddy-filters { grid-template-columns: minmax(180px, 1.5fr) repeat(3, minmax(120px, 1fr)); }
.buddy-filters .filter-actions { justify-content: flex-end; grid-column: 3 / -1; }
.recommendation-pagination { margin-top: 24px; justify-content: center; }
.matching-summary__copy .el-tag { align-self: flex-start; margin-top: 8px; }
.buddy-tabs { display: flex; flex-wrap: wrap; }
.invite-disclosure { color: var(--text-secondary); font-size: 13px; line-height: 1.8; }
@media (max-width: 760px) {
  .buddy-filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .buddy-filters > .el-input { grid-column: 1 / -1; }
  .buddy-filters .filter-actions { grid-column: 1 / -1; }
}
</style>

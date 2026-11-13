<script setup lang="ts">
import { Calendar, Check, Clock, DataAnalysis, Flag, Right, Timer } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import { ApiError } from '@/services/httpClient'
import { matchingDataApi } from '@/services/matchingData'
import { useProfileStore } from '@/stores/profile'
import { useStudyStore } from '@/stores/study'
import type { RecommendedBuddy } from '@/types/matching'

const studyStore = useStudyStore()
const profileStore = useProfileStore()
const topMatch = ref<RecommendedBuddy>()
const matchError = ref('')

const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const dateLabel = `${dayjs().format('M 月 D 日')} · ${weekdays[dayjs().day()]}`
const completedToday = computed(() => studyStore.todayTasks.filter((task) => task.completed).length)
const todayPercentage = computed(() =>
  studyStore.todayTasks.length ? Math.round((completedToday.value / studyStore.todayTasks.length) * 100) : 0,
)
const maxWeeklyMinutes = computed(() => Math.max(180, ...studyStore.weeklySeries.map((item) => item.minutes)))
const activeGoalProgress = computed(() => {
  const values = studyStore.activeGoals.map((goal) => studyStore.goalProgress(goal))
  return values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : 0
})
onMounted(async () => {
  if (!profileStore.apiMode) return
  try {
    topMatch.value = (await matchingDataApi.getRecommendations({ pageSize: 1 })).items[0]
  } catch (cause) {
    matchError.value = cause instanceof Error ? cause.message : '推荐暂时不可用'
  }
})

function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return hours > 0 ? `${hours}h ${rest}m` : `${rest}m`
}

async function toggleTask(goalId: string, taskId: string): Promise<void> {
  try {
    await studyStore.toggleTask(goalId, taskId)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '更新任务失败')
  }
}
</script>

<template>
  <div class="dashboard-view">
    <PageHeader
      :eyebrow="dateLabel"
      :title="`晚上好，${profileStore.profile.name} 👋`"
      description="今天的计划已经为你整理好。完成一件小事，也是在向目标稳定靠近。"
    >
      <template #actions>
        <RouterLink class="checkin-cta" to="/checkins"><Calendar /> 去打卡</RouterLink>
      </template>
    </PageHeader>

    <section class="stats-grid" aria-label="学习数据概览">
      <StatCard label="今日任务" :value="`${completedToday}/${studyStore.todayTasks.length}`" hint="完成后自动更新进度" :icon="Check" tone="violet" />
      <StatCard label="连续打卡" :value="studyStore.streakDays" suffix="天" hint="保持得很不错" :icon="Timer" tone="orange" />
      <StatCard label="本周专注" :value="formatMinutes(studyStore.weeklyMinutes)" hint="来自本周打卡记录" :icon="Clock" tone="cyan" />
      <StatCard label="进行中目标" :value="studyStore.activeGoals.length" suffix="个" :hint="`平均进度 ${activeGoalProgress}%`" :icon="Flag" tone="green" />
    </section>

    <div class="dashboard-grid">
      <section class="today-panel surface-card">
        <div class="section-title">
          <div><h2>今日任务</h2><p>优先完成最重要的三件事</p></div>
          <RouterLink class="text-button" to="/goals">管理目标 <Right /></RouterLink>
        </div>
        <div v-if="studyStore.todayTasks.length" class="task-list">
          <label
            v-for="task in studyStore.todayTasks"
            :key="task.id"
            class="task-item"
            :class="{ 'is-done': task.completed }"
          >
            <el-checkbox
              :model-value="task.completed"
              :aria-label="`${task.completed ? '取消完成' : '标记完成'}：${task.title}`"
              @change="toggleTask(task.goalId, task.id)"
            />
            <span class="task-item__color" :style="{ background: task.goalColor }"></span>
            <span class="task-item__copy">
              <strong>{{ task.title }}</strong>
              <small>{{ task.goalTitle }} · 预计 {{ task.estimatedMinutes }} 分钟</small>
            </span>
            <span class="task-item__status">{{ task.completed ? '已完成' : '待完成' }}</span>
          </label>
        </div>
        <EmptyState v-else title="今天还没有任务" description="在目标管理中添加一项今天要完成的任务吧。">
          <el-button type="primary" @click="$router.push('/goals')">添加任务</el-button>
        </EmptyState>
        <div v-if="studyStore.todayTasks.length" class="today-progress">
          <div><span>今日完成度</span><strong>{{ todayPercentage }}%</strong></div>
          <el-progress :percentage="todayPercentage" :show-text="false" :stroke-width="9" />
        </div>
      </section>

      <aside class="focus-panel">
        <section class="focus-card">
          <span class="focus-card__eyebrow">今日专注目标</span>
          <div class="focus-ring" :style="{ '--progress': `${todayPercentage * 3.6}deg` }">
            <div><strong>{{ todayPercentage }}%</strong><small>任务完成</small></div>
          </div>
          <p v-if="completedToday < studyStore.todayTasks.length">再完成 {{ studyStore.todayTasks.length - completedToday }} 项，就能收好今天的计划。</p>
          <p v-else>今日任务已完成，记得为这份认真留下打卡。</p>
          <RouterLink to="/checkins">记录今天的学习 <Right /></RouterLink>
        </section>

        <section v-if="topMatch" class="match-card surface-card">
          <div class="match-card__top">
            <span class="avatar">{{ topMatch.avatar }}</span>
            <div><small>今日高匹配搭子</small><strong>{{ topMatch.name }}</strong></div>
            <b>{{ topMatch.score }}<small>分</small></b>
          </div>
          <p>{{ topMatch.reasons.slice(0, 2).join(' · ') }}</p>
          <RouterLink class="text-button" to="/buddies">查看推荐 <Right /></RouterLink>
        </section>
        <section v-else class="match-card surface-card">
          <p>{{ matchError || '完善匹配档案，寻找一起学习的同行者。' }}</p>
          <RouterLink class="text-button" to="/buddies">寻找学习搭子 <Right /></RouterLink>
        </section>
      </aside>
    </div>

    <div class="insight-grid">
      <section class="weekly-card surface-card">
        <div class="section-title">
          <div><h2>本周学习节奏</h2><p>数据来自你的每日打卡</p></div>
          <span class="total-badge"><DataAnalysis /> 共 {{ formatMinutes(studyStore.weeklyMinutes) }}</span>
        </div>
        <div class="weekly-chart" role="img" aria-label="本周每天学习时长柱状图">
          <div v-for="item in studyStore.weeklySeries" :key="item.date" class="bar-column">
            <span class="bar-value">{{ item.minutes ? `${item.minutes}m` : '—' }}</span>
            <div class="bar-track"><span :style="{ height: `${Math.max(4, (item.minutes / maxWeeklyMinutes) * 100)}%` }"></span></div>
            <small>{{ item.label }}</small>
          </div>
        </div>
      </section>

      <section class="goals-panel surface-card">
        <div class="section-title">
          <div><h2>目标进度</h2><p>进行中的学习方向</p></div>
          <RouterLink class="text-button" to="/goals">全部 <Right /></RouterLink>
        </div>
        <div class="mini-goal-list">
          <article v-for="goal in studyStore.activeGoals.slice(0, 3)" :key="goal.id">
            <span class="mini-goal-icon" :style="{ color: goal.color, background: `${goal.color}14` }"><Flag /></span>
            <div>
              <strong>{{ goal.title }}</strong>
              <el-progress :percentage="studyStore.goalProgress(goal)" :stroke-width="7" />
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.checkin-cta { display: inline-flex; min-height: 42px; align-items: center; padding: 0 18px; border-radius: 11px; color: #fff; background: linear-gradient(135deg, var(--primary), #7465e8); box-shadow: 0 9px 22px rgba(91, 92, 226, 0.2); font-size: 13px; font-weight: 750; gap: 7px; text-decoration: none; }
.checkin-cta svg { width: 17px; }
.stats-grid { display: grid; margin-bottom: 20px; gap: 14px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.dashboard-grid { display: grid; align-items: stretch; gap: 20px; grid-template-columns: minmax(0, 1.75fr) minmax(260px, 0.75fr); }
.today-panel { padding: 24px; }
.section-title .text-button svg { width: 14px; }
.task-list { display: flex; flex-direction: column; }
.task-item { position: relative; display: flex; min-width: 0; align-items: center; padding: 15px 4px; border-bottom: 1px solid #f0f1f5; cursor: pointer; gap: 12px; }
.task-item:hover { background: linear-gradient(90deg, transparent, #fafaff, transparent); }
.task-item__color { width: 4px; height: 32px; flex: 0 0 auto; border-radius: 4px; opacity: 0.65; }
.task-item__copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.task-item__copy strong { overflow: hidden; color: var(--text-strong); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.task-item__copy small { margin-top: 4px; color: var(--text-muted); font-size: 10px; }
.task-item__status { padding: 5px 8px; border-radius: 999px; color: #8c8fa2; background: #f2f3f7; font-size: 9px; font-weight: 700; }
.task-item.is-done .task-item__copy strong { color: var(--text-muted); text-decoration: line-through; }
.task-item.is-done .task-item__status { color: #168369; background: #e6f7f1; }
.today-progress { padding: 15px 16px; margin-top: 19px; border-radius: 13px; background: #f7f7fc; }
.today-progress > div { display: flex; justify-content: space-between; margin-bottom: 9px; color: var(--text-secondary); font-size: 11px; }
.today-progress strong { color: var(--primary); }
.focus-panel { display: flex; gap: 14px; flex-direction: column; }
.focus-card { position: relative; display: flex; flex: 1; align-items: center; padding: 25px 21px; overflow: hidden; border-radius: 19px; color: #fff; background: linear-gradient(145deg, #5354d3, #735fdf); box-shadow: 0 18px 42px rgba(77, 72, 190, 0.22); text-align: center; flex-direction: column; }
.focus-card::after { position: absolute; right: -50px; bottom: -70px; width: 180px; height: 180px; border: 1px solid rgba(255, 255, 255, 0.14); border-radius: 50%; content: ''; }
.focus-card__eyebrow { align-self: flex-start; color: #dedfff; font-size: 10px; font-weight: 800; letter-spacing: 0.08em; }
.focus-ring { display: grid; width: 124px; height: 124px; margin: 21px 0 14px; place-items: center; border-radius: 50%; background: conic-gradient(#fff var(--progress), rgba(255, 255, 255, 0.15) 0); }
.focus-ring::after { position: absolute; width: 105px; height: 105px; border-radius: 50%; content: ''; background: #6359da; }
.focus-ring > div { z-index: 1; display: flex; flex-direction: column; }
.focus-ring strong { font-size: 26px; letter-spacing: -0.04em; }
.focus-ring small { color: #d8d9ff; font-size: 8px; }
.focus-card p { z-index: 1; max-width: 220px; margin: 0; color: #e2e2ff; font-size: 11px; line-height: 1.7; }
.focus-card a { z-index: 1; display: inline-flex; align-items: center; margin-top: 14px; color: #fff; font-size: 11px; font-weight: 750; gap: 5px; text-decoration: none; }
.focus-card a svg { width: 12px; }
.match-card { padding: 17px; }
.match-card__top { display: flex; align-items: center; gap: 10px; }
.match-card__top .avatar { width: 38px; height: 38px; border-radius: 12px; font-size: 12px; }
.match-card__top > div { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.match-card__top div small { color: var(--text-muted); font-size: 8px; }
.match-card__top div strong { font-size: 13px; }
.match-card__top > b { color: var(--primary); font-size: 20px; }
.match-card__top > b small { font-size: 8px; }
.match-card > p { overflow: hidden; margin: 10px 0 6px; color: var(--text-secondary); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.match-card .text-button { font-size: 10px; }
.insight-grid { display: grid; margin-top: 20px; gap: 20px; grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.85fr); }
.weekly-card, .goals-panel { padding: 24px; }
.total-badge { display: inline-flex; align-items: center; padding: 6px 9px; border-radius: 999px; color: var(--primary); background: var(--primary-soft); font-size: 9px; font-weight: 750; gap: 5px; }
.total-badge svg { width: 13px; }
.weekly-chart { display: grid; height: 185px; align-items: stretch; padding-top: 9px; gap: 12px; grid-template-columns: repeat(7, 1fr); }
.bar-column { display: flex; height: 100%; align-items: center; flex-direction: column; }
.bar-value { height: 21px; color: var(--text-muted); font-size: 8px; }
.bar-track { position: relative; display: flex; width: min(28px, 60%); flex: 1; align-items: flex-end; border-radius: 7px; background: #f0f1f7; overflow: hidden; }
.bar-track span { width: 100%; min-height: 4px; border-radius: 7px; background: linear-gradient(180deg, #8a84ef, #5b5ce2); transition: height 0.35s ease; }
.bar-column small { margin-top: 8px; color: var(--text-secondary); font-size: 9px; }
.mini-goal-list { display: flex; gap: 18px; flex-direction: column; }
.mini-goal-list article { display: flex; align-items: center; gap: 12px; }
.mini-goal-icon { display: grid; width: 39px; height: 39px; flex: 0 0 auto; place-items: center; border-radius: 12px; }
.mini-goal-icon svg { width: 18px; }
.mini-goal-list article > div { min-width: 0; flex: 1; }
.mini-goal-list strong { display: block; overflow: hidden; margin-bottom: 6px; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.mini-goal-list :deep(.el-progress__text) { min-width: 31px; font-size: 9px !important; }

@media (max-width: 1180px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .dashboard-grid, .insight-grid { grid-template-columns: 1fr; }
  .focus-panel { display: grid; grid-template-columns: 1fr 1fr; }
}

@media (max-width: 620px) {
  .stats-grid { grid-template-columns: 1fr 1fr; gap: 9px; }
  .stats-grid :deep(.stat-card) { padding: 14px; }
  .stats-grid :deep(.stat-card__icon) { width: 36px; height: 36px; flex-basis: 36px; }
  .stats-grid :deep(.stat-card strong) { font-size: 20px; }
  .today-panel, .weekly-card, .goals-panel { padding: 18px; }
  .task-item__status { display: none; }
  .focus-panel { display: flex; }
  .focus-card { min-height: 340px; }
  .weekly-chart { gap: 5px; }
  .bar-track { width: min(22px, 70%); }
}
</style>

<script setup lang="ts">
import { Calendar, Clock, EditPen, Plus, Sunny, Timer } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import CheckinShareDialog from '@/components/CheckinShareDialog.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import { ApiError } from '@/services/httpClient'
import { useStudyStore } from '@/stores/study'
import { MOODS, type Checkin, type Mood } from '@/types/models'

interface CheckinForm {
  duration: number
  content: string
  mood: Mood
  goalId: string
}

const studyStore = useStudyStore()
const calendarDate = ref(new Date())
const dialogOpen = ref(false)
const shareOpen = ref(false)
const shareRecord = ref<Checkin | null>(null)
const submitting = ref(false)
function openShare(record: Checkin): void { shareRecord.value = record; shareOpen.value = true }
const form = ref<CheckinForm>({ duration: 180, content: '', mood: '专注在线', goalId: '' })

const selectedDate = computed(() => dayjs(calendarDate.value).format('YYYY-MM-DD'))
const selectedDateLabel = computed(() => dayjs(calendarDate.value).format('YYYY年M月D日'))
const selectedRecords = computed(() => studyStore.checkins.filter((item) => item.date === selectedDate.value))
const selectedMinutes = computed(() => selectedRecords.value.reduce((sum, item) => sum + item.duration, 0))
const isFutureDate = computed(() => dayjs(selectedDate.value).isAfter(dayjs(), 'day'))
const checkinDates = computed(() => new Set(studyStore.checkins.map((item) => item.date)))
const monthRecords = computed(() =>
  studyStore.checkins.filter((item) => dayjs(item.date).isSame(dayjs(calendarDate.value), 'month')),
)
const monthMinutes = computed(() => monthRecords.value.reduce((sum, item) => sum + item.duration, 0))
const monthDays = computed(() => new Set(monthRecords.value.map((item) => item.date)).size)
const history = computed(() => [...studyStore.checkins].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 8))

function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (hours === 0) return `${rest} 分钟`
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`
}

function openCheckin(): void {
  if (isFutureDate.value) {
    ElMessage.warning('不能为未来日期提交打卡')
    return
  }
  form.value = { duration: 180, content: '', mood: '专注在线', goalId: studyStore.activeGoals[0]?.id ?? '' }
  dialogOpen.value = true
}

async function submitCheckin(): Promise<void> {
  if (submitting.value) return
  if (!form.value.content.trim()) {
    ElMessage.warning('请简要记录今天学了什么')
    return
  }
  submitting.value = true
  try {
    await studyStore.addCheckin({
      date: selectedDate.value,
      duration: form.value.duration,
      content: form.value.content.trim(),
      mood: form.value.mood,
      goalId: form.value.goalId || undefined,
    })
    dialogOpen.value = false
    ElMessage.success(`已记录 ${formatDuration(form.value.duration)} 的学习`)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '提交打卡失败')
  } finally { submitting.value = false }
}

function goalTitle(goalId?: string): string {
  return studyStore.goals.find((goal) => goal.id === goalId)?.title ?? '自由学习'
}

function moodEmoji(mood: Mood): string {
  return { 状态极佳: '✨', 专注在线: '🎯', 稳步推进: '🌱', 有点疲惫: '🌙' }[mood]
}
</script>

<template>
  <div class="checkins-view">
    <PageHeader eyebrow="CHECK IN" title="学习打卡" description="不追求每一天都完美，只记录每一次真实投入，让坚持有迹可循。">
      <template #actions>
        <el-button type="primary" :icon="EditPen" @click="openCheckin">记录今日学习</el-button>
      </template>
    </PageHeader>

    <section class="stats-grid" aria-label="打卡数据概览">
      <StatCard label="连续打卡" :value="studyStore.streakDays" suffix="天" hint="从最近一次打卡连续计算" :icon="Sunny" tone="orange" />
      <StatCard label="本月打卡" :value="monthDays" suffix="天" :hint="`${dayjs(calendarDate).format('M月')}累计记录`" :icon="Calendar" tone="violet" />
      <StatCard label="本月时长" :value="Math.round(monthMinutes / 60 * 10) / 10" suffix="小时" hint="来自当前显示月份" :icon="Clock" tone="cyan" />
      <StatCard label="累计时长" :value="Math.round(studyStore.totalMinutes / 60)" suffix="小时" hint="当前账号全部记录" :icon="Timer" tone="green" />
    </section>

    <div class="checkin-grid">
      <section class="calendar-card surface-card">
        <el-calendar v-model="calendarDate">
          <template #header="{ date }">
            <div class="calendar-header">
              <div><h2>打卡日历</h2><p>{{ date }} · 点击日期查看记录</p></div>
              <button type="button" @click="calendarDate = new Date()">回到今天</button>
            </div>
          </template>
          <template #date-cell="{ data }">
            <div class="date-cell" :class="{ checked: checkinDates.has(data.day), future: dayjs(data.day).isAfter(dayjs(), 'day') }">
              <span>{{ dayjs(data.day).date() }}</span>
              <i v-if="checkinDates.has(data.day)" aria-label="已打卡"><span>✓</span></i>
            </div>
          </template>
        </el-calendar>
      </section>

      <aside class="day-panel surface-card">
        <div class="day-panel__date">
          <span>{{ dayjs(calendarDate).format('MM') }}<small>月</small></span>
          <div><strong>{{ selectedDateLabel }}</strong><small>{{ selectedDate === dayjs().format('YYYY-MM-DD') ? '今天' : '所选日期' }}</small></div>
        </div>

        <div v-if="selectedRecords.length" class="selected-summary">
          <div><span>当日累计</span><strong>{{ formatDuration(selectedMinutes) }}</strong></div>
          <div><span>记录次数</span><strong>{{ selectedRecords.length }} 次</strong></div>
        </div>

        <div v-if="selectedRecords.length" class="selected-records">
          <article v-for="record in selectedRecords" :key="record.id" :data-checkin-id="record.id">
            <span class="record-mood">{{ moodEmoji(record.mood) }}</span>
            <div><strong>{{ goalTitle(record.goalId) }}</strong><p>{{ record.content }}</p><small>{{ record.mood }} · {{ record.duration }} 分钟</small><el-button v-if="studyStore.apiMode" text type="primary" @click="openShare(record)">分享到小组</el-button></div>
          </article>
        </div>
        <EmptyState v-else :title="isFutureDate ? '未来值得期待' : '这一天还没有记录'" :description="isFutureDate ? '未来日期暂不能打卡，先完成今天的学习吧。' : '补上一条真实的学习记录，让日历亮起来。'" symbol="◌">
          <el-button v-if="!isFutureDate" type="primary" :icon="Plus" @click="openCheckin">添加打卡</el-button>
        </EmptyState>

        <el-button v-if="selectedRecords.length && !isFutureDate" class="add-another" plain :icon="Plus" @click="openCheckin">再记录一段学习</el-button>
      </aside>
    </div>

    <section class="history-card surface-card">
      <div class="section-title">
        <div><h2>最近打卡</h2><p>回看近期的学习内容与状态</p></div>
        <span>展示最近 {{ history.length }} 条</span>
      </div>
      <div class="history-list">
        <article v-for="record in history" :key="record.id" :data-history-checkin="record.id">
          <time :datetime="record.date"><strong>{{ dayjs(record.date).format('DD') }}</strong><small>{{ dayjs(record.date).format('M月') }}</small></time>
          <span class="timeline-dot"></span>
          <div class="history-copy">
            <strong>{{ record.content }}</strong>
            <span>{{ goalTitle(record.goalId) }} · {{ record.mood }}</span>
            <el-button v-if="studyStore.apiMode" text type="primary" @click="openShare(record)">分享到小组</el-button>
          </div>
          <b>{{ record.duration }}<small>分钟</small></b>
        </article>
      </div>
    </section>

    <el-dialog v-model="dialogOpen" :title="`学习打卡 · ${selectedDateLabel}`" width="530px" destroy-on-close>
      <div class="checkin-form">
        <div class="prototype-banner"><strong>{{ studyStore.apiMode ? '账号数据' : '开发演示' }}</strong> {{ studyStore.apiMode ? '本次打卡将安全保存到当前账号。' : '本次打卡只保存在当前浏览器。' }}</div>
        <label>关联目标</label>
        <el-select v-model="form.goalId" placeholder="可选择一个目标" clearable>
          <el-option v-for="goal in studyStore.activeGoals" :key="goal.id" :label="goal.title" :value="goal.id" />
        </el-select>
        <label>学习时长</label>
        <div class="duration-row">
          <el-slider v-model="form.duration" :min="15" :max="480" :step="15" show-stops />
          <strong>{{ formatDuration(form.duration) }}</strong>
        </div>
        <label>今天学了什么</label>
        <el-input v-model="form.content" type="textarea" :rows="4" maxlength="160" show-word-limit placeholder="例如：完成数据结构二叉树章节，整理了 6 道错题……" />
        <label>学习状态</label>
        <div class="mood-options" role="radiogroup" aria-label="选择学习状态">
          <button
            v-for="mood in MOODS"
            :key="mood"
            type="button"
            :class="{ active: form.mood === mood }"
            role="radio"
            :aria-checked="form.mood === mood"
            @click="form.mood = mood"
          ><span>{{ moodEmoji(mood) }}</span>{{ mood }}</button>
        </div>
      </div>
      <template #footer>
        <el-button :disabled="submitting" @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCheckin">提交打卡</el-button>
      </template>
    </el-dialog>
    <CheckinShareDialog v-model="shareOpen" :checkin="shareRecord" />
  </div>
</template>

<style scoped>
.stats-grid { display: grid; margin-bottom: 20px; gap: 14px; grid-template-columns: repeat(4, 1fr); }
.checkin-grid { display: grid; align-items: stretch; gap: 20px; grid-template-columns: minmax(0, 1.55fr) minmax(300px, 0.65fr); }
.calendar-card { min-width: 0; overflow: hidden; }
.calendar-card :deep(.el-calendar) { --el-calendar-cell-width: auto; padding: 0; border-radius: 18px; }
.calendar-card :deep(.el-calendar__header) { padding: 21px 23px; border-bottom-color: var(--border-light); }
.calendar-card :deep(.el-calendar__body) { padding: 10px 18px 20px; }
.calendar-card :deep(.el-calendar-table th) { padding: 12px 0; color: var(--text-muted); font-size: 10px; font-weight: 700; }
.calendar-card :deep(.el-calendar-table td) { border: 0; }
.calendar-card :deep(.el-calendar-table .el-calendar-day) { height: 75px; padding: 4px; }
.calendar-card :deep(.el-calendar-table td.is-selected) { background: transparent; }
.calendar-header { display: flex; width: 100%; align-items: center; justify-content: space-between; }
.calendar-header h2 { margin: 0; font-size: 17px; }
.calendar-header p { margin: 4px 0 0; color: var(--text-muted); font-size: 9px; }
.calendar-header button { padding: 7px 11px; border: 1px solid #e1e2ec; border-radius: 8px; color: var(--primary); background: #fff; cursor: pointer; font-size: 9px; font-weight: 750; }
.date-cell { display: flex; height: 100%; align-items: center; justify-content: center; border: 1px solid transparent; border-radius: 11px; color: var(--text-secondary); gap: 5px; flex-direction: column; }
.date-cell > span { font-size: 11px; }
.date-cell i { display: grid; width: 18px; height: 18px; place-items: center; border-radius: 6px; color: #fff; background: var(--primary); font-size: 8px; font-style: normal; }
.date-cell.checked { background: #f5f5ff; }
.date-cell.future { color: #c4c6d0; }
.calendar-card :deep(td.is-selected .date-cell) { border-color: var(--primary); color: var(--primary); background: #eeeeff; font-weight: 800; }
.day-panel { display: flex; min-height: 535px; padding: 23px; flex-direction: column; }
.day-panel__date { display: flex; align-items: center; padding-bottom: 18px; border-bottom: 1px solid var(--border-light); gap: 13px; }
.day-panel__date > span { display: grid; width: 50px; height: 50px; place-items: center; border-radius: 14px; color: #fff; background: linear-gradient(145deg, var(--primary), #7665e5); font-size: 20px; font-weight: 900; line-height: 1; grid-template-columns: auto auto; }
.day-panel__date > span small { margin-left: 2px; font-size: 7px; }
.day-panel__date > div { display: flex; flex-direction: column; }
.day-panel__date strong { font-size: 13px; }
.day-panel__date div small { margin-top: 3px; color: var(--text-muted); font-size: 9px; }
.selected-summary { display: grid; padding: 14px 0; border-bottom: 1px solid var(--border-light); grid-template-columns: 1fr 1fr; }
.selected-summary div { display: flex; flex-direction: column; }
.selected-summary span { color: var(--text-muted); font-size: 8px; }
.selected-summary strong { margin-top: 3px; font-size: 13px; }
.selected-records { max-height: 330px; overflow-y: auto; }
.selected-records article { display: flex; padding: 15px 0; border-bottom: 1px solid var(--border-light); gap: 10px; }
.record-mood { display: grid; width: 34px; height: 34px; flex: 0 0 auto; place-items: center; border-radius: 11px; background: #f4f4fa; }
.selected-records article > div { min-width: 0; }
.selected-records strong { font-size: 11px; }
.selected-records p { margin: 5px 0; color: var(--text-secondary); font-size: 10px; line-height: 1.6; }
.selected-records small { color: var(--text-muted); font-size: 8px; }
.add-another { margin-top: auto; }
.history-card { padding: 24px; margin-top: 20px; }
.section-title > span { color: var(--text-muted); font-size: 9px; }
.history-list article { display: flex; min-width: 0; align-items: center; padding: 12px 5px; border-bottom: 1px solid var(--border-light); gap: 14px; }
.history-list article:last-child { border-bottom: 0; }
.history-list time { display: flex; width: 34px; align-items: center; flex-direction: column; }
.history-list time strong { font-size: 15px; }
.history-list time small { color: var(--text-muted); font-size: 8px; }
.timeline-dot { width: 8px; height: 8px; border: 2px solid #fff; border-radius: 50%; background: var(--primary); box-shadow: 0 0 0 2px #dcdcff; }
.history-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.history-copy strong { overflow: hidden; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.history-copy span { margin-top: 3px; color: var(--text-muted); font-size: 8px; }
.history-list article > b { color: var(--primary); font-size: 15px; }
.history-list article > b small { margin-left: 2px; color: var(--text-muted); font-size: 7px; }
.checkin-form { display: flex; gap: 8px; flex-direction: column; }
.checkin-form > label { margin-top: 8px; color: var(--text-secondary); font-size: 11px; font-weight: 700; }
.duration-row { display: flex; align-items: center; gap: 18px; }
.duration-row :deep(.el-slider) { flex: 1; }
.duration-row strong { min-width: 88px; color: var(--primary); font-size: 11px; text-align: right; }
.mood-options { display: grid; gap: 7px; grid-template-columns: repeat(4, 1fr); }
.mood-options button { display: flex; min-height: 62px; align-items: center; justify-content: center; padding: 6px; border: 1px solid var(--border-light); border-radius: 11px; color: var(--text-secondary); background: #fff; cursor: pointer; font-size: 9px; gap: 3px; flex-direction: column; }
.mood-options button span { font-size: 17px; }
.mood-options button.active { color: var(--primary); border-color: #bfc0ef; background: var(--primary-soft); font-weight: 750; }

@media (max-width: 1120px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .checkin-grid { grid-template-columns: 1fr; }
  .day-panel { min-height: 420px; }
}

@media (max-width: 620px) {
  .stats-grid { grid-template-columns: 1fr 1fr; gap: 9px; }
  .stats-grid :deep(.stat-card) { padding: 14px; }
  .stats-grid :deep(.stat-card__icon) { display: none; }
  .calendar-card :deep(.el-calendar__header) { padding: 17px; }
  .calendar-card :deep(.el-calendar__body) { padding: 7px 7px 15px; }
  .calendar-card :deep(.el-calendar-table .el-calendar-day) { height: 53px; padding: 2px; }
  .date-cell { gap: 2px; }
  .date-cell i { width: 14px; height: 14px; }
  .calendar-header p { display: none; }
  .day-panel, .history-card { padding: 18px; }
  .mood-options { grid-template-columns: repeat(2, 1fr); }
}
</style>

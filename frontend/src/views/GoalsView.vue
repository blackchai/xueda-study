<script setup lang="ts">
import { Calendar, Check, Delete, Edit, Flag, MoreFilled, Plus, Tickets } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { computed, ref } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import PageHeader from '@/components/PageHeader.vue'
import { ApiError } from '@/services/httpClient'
import { useStudyStore } from '@/stores/study'
import { GOAL_CATEGORIES, type GoalCategory, type GoalStatus, type StudyGoal } from '@/types/models'

interface GoalForm {
  title: string
  description: string
  category: GoalCategory
  tagsText: string
  dateRange: string[]
  status: GoalStatus
  color: string
}

interface TaskForm {
  title: string
  dueDate: string
  estimatedMinutes: number
}

const studyStore = useStudyStore()
const activeFilter = ref<'全部' | GoalStatus>('全部')
const goalDialogOpen = ref(false)
const taskDialogOpen = ref(false)
const editingGoalId = ref<string | null>(null)
const editingTaskId = ref<string | null>(null)
const selectedGoalId = ref<string | null>(null)
const goalFormRef = ref<FormInstance>()

const goalColors = ['#5b5ce2', '#15a98c', '#f59e5b', '#e3596b', '#248fca', '#8b5cd6']

function createEmptyGoal(): GoalForm {
  return {
    title: '',
    description: '',
    category: '考研',
    tagsText: '',
    dateRange: [dayjs().format('YYYY-MM-DD'), dayjs().add(90, 'day').format('YYYY-MM-DD')],
    status: '进行中',
    color: goalColors[0] ?? '#5b5ce2',
  }
}

const goalForm = ref<GoalForm>(createEmptyGoal())
const taskForm = ref<TaskForm>({ title: '', dueDate: dayjs().format('YYYY-MM-DD'), estimatedMinutes: 60 })

const goalRules: FormRules = {
  title: [
    { required: true, message: '请输入目标名称', trigger: 'blur' },
    { min: 2, max: 30, message: '目标名称为 2—30 个字符', trigger: 'blur' },
  ],
  category: [{ required: true, message: '请选择学习方向', trigger: 'change' }],
  dateRange: [{ type: 'array', required: true, min: 2, message: '请选择起止日期', trigger: 'change' }],
}

const filters: Array<'全部' | GoalStatus> = ['全部', '进行中', '已完成', '已暂停']
const filteredGoals = computed(() =>
  activeFilter.value === '全部' ? studyStore.goals : studyStore.goals.filter((goal) => goal.status === activeFilter.value),
)
const selectedGoal = computed(() => studyStore.goals.find((goal) => goal.id === selectedGoalId.value))

function openCreateGoal(): void {
  editingGoalId.value = null
  goalForm.value = createEmptyGoal()
  goalDialogOpen.value = true
}

function openEditGoal(goal: StudyGoal): void {
  editingGoalId.value = goal.id
  goalForm.value = {
    title: goal.title,
    description: goal.description,
    category: goal.category,
    tagsText: goal.tags.join('、'),
    dateRange: [goal.startDate, goal.targetDate],
    status: goal.status,
    color: goal.color,
  }
  goalDialogOpen.value = true
}

async function saveGoal(): Promise<void> {
  if (!goalFormRef.value) return
  const valid = await goalFormRef.value.validate().catch(() => false)
  if (!valid) return

  const [startDate = '', targetDate = ''] = goalForm.value.dateRange
  const payload = {
    title: goalForm.value.title.trim(),
    description: goalForm.value.description.trim(),
    category: goalForm.value.category,
    tags: goalForm.value.tagsText.split(/[、,，\s]+/).map((tag) => tag.trim()).filter(Boolean),
    startDate,
    targetDate,
    status: goalForm.value.status,
    color: goalForm.value.color,
  }

  try {
    if (editingGoalId.value) {
      await studyStore.updateGoal(editingGoalId.value, payload)
      ElMessage.success('目标已更新')
    } else {
      await studyStore.addGoal({ ...payload, tasks: [] })
      ElMessage.success('新目标已创建')
    }
    goalDialogOpen.value = false
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '保存目标失败')
  }
}

async function removeGoal(goal: StudyGoal): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除“${goal.title}”后，其任务也会一并移除。`,
      '确认删除目标',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    // User cancelled the confirmation dialog.
    return
  }
  try {
    await studyStore.removeGoal(goal.id)
    ElMessage.success('目标已删除')
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '删除目标失败')
  }
}

function openTasks(goal: StudyGoal): void {
  selectedGoalId.value = goal.id
  editingTaskId.value = null
  taskForm.value = { title: '', dueDate: dayjs().format('YYYY-MM-DD'), estimatedMinutes: 60 }
  taskDialogOpen.value = true
}

function editTask(taskId: string): void {
  const task = selectedGoal.value?.tasks.find((item) => item.id === taskId)
  if (!task) return
  editingTaskId.value = task.id
  taskForm.value = { title: task.title, dueDate: task.dueDate, estimatedMinutes: task.estimatedMinutes }
}

async function saveTask(): Promise<void> {
  if (!selectedGoalId.value || !taskForm.value.title.trim()) {
    ElMessage.warning('请填写任务名称')
    return
  }
  try {
    if (editingTaskId.value) {
      await studyStore.updateTask(selectedGoalId.value, editingTaskId.value, {
        title: taskForm.value.title.trim(),
        dueDate: taskForm.value.dueDate,
        estimatedMinutes: taskForm.value.estimatedMinutes,
      })
      ElMessage.success('任务已更新')
    } else {
      await studyStore.addTask(selectedGoalId.value, { ...taskForm.value, title: taskForm.value.title.trim(), completed: false })
      ElMessage.success('任务已添加')
    }
    editingTaskId.value = null
    taskForm.value = { title: '', dueDate: dayjs().format('YYYY-MM-DD'), estimatedMinutes: 60 }
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '保存任务失败')
  }
}

async function toggleTask(goalId: string, taskId: string): Promise<void> {
  try {
    await studyStore.toggleTask(goalId, taskId)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '更新任务失败')
  }
}

async function removeTask(goalId: string, taskId: string): Promise<void> {
  try {
    await studyStore.removeTask(goalId, taskId)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '删除任务失败')
  }
}

function cancelTaskEdit(): void {
  editingTaskId.value = null
  taskForm.value = { title: '', dueDate: dayjs().format('YYYY-MM-DD'), estimatedMinutes: 60 }
}

function daysRemaining(goal: StudyGoal): string {
  const days = dayjs(goal.targetDate).diff(dayjs(), 'day')
  if (goal.status === '已完成') return '已达成'
  if (days < 0) return `已超期 ${Math.abs(days)} 天`
  if (days === 0) return '今天截止'
  return `还剩 ${days} 天`
}

function statusType(status: GoalStatus): 'success' | 'warning' | 'info' {
  if (status === '已完成') return 'success'
  if (status === '已暂停') return 'info'
  return 'warning'
}
</script>

<template>
  <div class="goals-view">
    <PageHeader eyebrow="GOAL CENTER" title="目标管理" description="把远方拆成一段段可完成的路，每个任务都会汇入目标的真实进度。">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="openCreateGoal">创建目标</el-button>
      </template>
    </PageHeader>

    <div class="goal-overview">
      <div><span>全部目标</span><strong>{{ studyStore.goals.length }}</strong><small>个</small></div>
      <i></i>
      <div><span>进行中</span><strong>{{ studyStore.activeGoals.length }}</strong><small>个</small></div>
      <i></i>
      <div><span>已完成任务</span><strong>{{ studyStore.totalCompletedTasks }}</strong><small>项</small></div>
      <div class="overview-illustration" aria-hidden="true"><Flag /><span></span><span></span></div>
    </div>

    <div class="goal-toolbar">
      <div class="filter-tabs" role="tablist" aria-label="目标状态筛选">
        <button
          v-for="filter in filters"
          :key="filter"
          type="button"
          :class="{ active: activeFilter === filter }"
          role="tab"
          :aria-selected="activeFilter === filter"
          @click="activeFilter = filter"
        >
          {{ filter }}
        </button>
      </div>
      <span>共 {{ filteredGoals.length }} 个目标</span>
    </div>

    <section v-if="filteredGoals.length" class="goals-grid" aria-label="目标列表">
      <article v-for="goal in filteredGoals" :key="goal.id" class="goal-card surface-card surface-card--interactive">
        <div class="goal-card__top">
          <span class="goal-icon" :style="{ color: goal.color, background: `${goal.color}14` }"><Flag /></span>
          <el-tag size="small" effect="light" :type="statusType(goal.status)">{{ goal.status }}</el-tag>
          <el-dropdown trigger="click">
            <button class="more-button" type="button" :aria-label="`管理目标：${goal.title}`"><MoreFilled /></button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :icon="Edit" @click="openEditGoal(goal)">编辑目标</el-dropdown-item>
                <el-dropdown-item :icon="Tickets" @click="openTasks(goal)">管理任务</el-dropdown-item>
                <el-dropdown-item :icon="Delete" divided @click="removeGoal(goal)">删除目标</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <span class="goal-category">{{ goal.category }}</span>
        <h2>{{ goal.title }}</h2>
        <p>{{ goal.description || '暂未填写目标说明。' }}</p>

        <div class="tag-list">
          <span v-for="tag in goal.tags.slice(0, 3)" :key="tag" class="soft-tag">{{ tag }}</span>
        </div>

        <div class="goal-progress">
          <div><span>整体进度</span><strong>{{ studyStore.goalProgress(goal) }}%</strong></div>
          <el-progress :percentage="studyStore.goalProgress(goal)" :show-text="false" :stroke-width="9" :color="goal.color" />
        </div>

        <div class="goal-meta">
          <span><Calendar /> {{ dayjs(goal.targetDate).format('YYYY.MM.DD') }}</span>
          <span :class="{ overdue: dayjs(goal.targetDate).isBefore(dayjs(), 'day') && goal.status !== '已完成' }">{{ daysRemaining(goal) }}</span>
          <span>{{ goal.tasks.filter((task) => task.completed).length }}/{{ goal.tasks.length }} 任务</span>
        </div>

        <button class="manage-tasks-button" type="button" @click="openTasks(goal)">
          <Tickets /> 管理任务
        </button>
      </article>

      <button class="create-goal-card" type="button" @click="openCreateGoal">
        <span><Plus /></span>
        <strong>创建一个新目标</strong>
        <small>从清晰的方向开始规划</small>
      </button>
    </section>

    <EmptyState v-else title="当前筛选下没有目标" description="切换状态查看，或创建一个新的学习目标。">
      <el-button type="primary" :icon="Plus" @click="openCreateGoal">创建目标</el-button>
    </EmptyState>

    <el-dialog v-model="goalDialogOpen" :title="editingGoalId ? '编辑学习目标' : '创建学习目标'" width="590px" destroy-on-close>
      <el-form ref="goalFormRef" :model="goalForm" :rules="goalRules" label-position="top">
        <el-form-item label="目标名称" prop="title">
          <el-input v-model="goalForm.title" maxlength="30" show-word-limit placeholder="例如：计算机考研冲刺计划" />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="学习方向" prop="category">
            <el-select v-model="goalForm.category" placeholder="选择方向">
              <el-option v-for="category in GOAL_CATEGORIES" :key="category" :label="category" :value="category" />
            </el-select>
          </el-form-item>
          <el-form-item label="目标状态">
            <el-select v-model="goalForm.status">
              <el-option label="进行中" value="进行中" />
              <el-option label="已完成" value="已完成" />
              <el-option label="已暂停" value="已暂停" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="起止日期" prop="dateRange">
          <el-date-picker v-model="goalForm.dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="目标日期" range-separator="至" />
        </el-form-item>
        <el-form-item label="目标说明">
          <el-input v-model="goalForm.description" type="textarea" :rows="3" maxlength="120" show-word-limit placeholder="写下完成标准或复习范围" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="goalForm.tagsText" placeholder="使用空格、逗号或顿号分隔，例如：408 高等数学" />
        </el-form-item>
        <el-form-item label="识别颜色">
          <div class="color-picker" role="radiogroup" aria-label="目标颜色">
            <button
              v-for="color in goalColors"
              :key="color"
              type="button"
              :style="{ background: color }"
              :class="{ selected: goalForm.color === color }"
              :aria-label="`选择颜色 ${color}`"
              :aria-checked="goalForm.color === color"
              role="radio"
              @click="goalForm.color = color"
            ><Check v-if="goalForm.color === color" /></button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="goalDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="saveGoal">{{ editingGoalId ? '保存修改' : '创建目标' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taskDialogOpen" :title="`管理任务 · ${selectedGoal?.title ?? ''}`" width="720px" destroy-on-close>
      <div class="task-editor">
        <div class="task-editor__form">
          <el-input v-model="taskForm.title" placeholder="任务名称" @keyup.enter="saveTask" />
          <el-date-picker v-model="taskForm.dueDate" type="date" value-format="YYYY-MM-DD" placeholder="截止日期" />
          <el-input-number v-model="taskForm.estimatedMinutes" :min="10" :max="720" :step="10" aria-label="预计分钟数" />
          <el-button type="primary" @click="saveTask">{{ editingTaskId ? '保存' : '添加' }}</el-button>
          <el-button v-if="editingTaskId" @click="cancelTaskEdit">取消</el-button>
        </div>
        <p class="task-editor__hint">预计时长单位为分钟；任务完成状态会直接影响目标进度。</p>
        <div v-if="selectedGoal?.tasks.length" class="managed-task-list">
          <article v-for="task in selectedGoal.tasks" :key="task.id" :class="{ done: task.completed }">
            <el-checkbox :model-value="task.completed" :aria-label="`切换任务状态：${task.title}`" @change="toggleTask(selectedGoal?.id ?? '', task.id)" />
            <div><strong>{{ task.title }}</strong><small>{{ task.dueDate }} · {{ task.estimatedMinutes }} 分钟</small></div>
            <el-button circle text :icon="Edit" aria-label="编辑任务" @click="editTask(task.id)" />
            <el-button circle text type="danger" :icon="Delete" aria-label="删除任务" @click="removeTask(selectedGoal?.id ?? '', task.id)" />
          </article>
        </div>
        <EmptyState v-else title="还没有任务" description="添加第一项任务，目标进度就会开始计算。" symbol="＋" />
      </div>
      <template #footer>
        <el-button @click="taskDialogOpen = false">完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.goal-overview { position: relative; display: flex; min-height: 120px; align-items: center; padding: 25px 32px; margin-bottom: 22px; overflow: hidden; border-radius: 19px; color: #fff; background: linear-gradient(125deg, #5152cf, #6a60de 72%, #735bd5); box-shadow: 0 18px 42px rgba(75, 72, 185, 0.18); gap: 28px; }
.goal-overview > div:not(.overview-illustration) { z-index: 1; display: flex; align-items: baseline; gap: 4px; flex-wrap: wrap; }
.goal-overview span { width: 100%; color: #dbdcff; font-size: 10px; font-weight: 700; }
.goal-overview strong { font-size: 30px; letter-spacing: -0.04em; }
.goal-overview small { color: #d2d3ff; font-size: 10px; }
.goal-overview > i { width: 1px; height: 42px; background: rgba(255, 255, 255, 0.18); }
.overview-illustration { position: absolute; right: 35px; display: grid; width: 100px; height: 100px; place-items: center; border: 1px solid rgba(255, 255, 255, 0.13); border-radius: 50%; }
.overview-illustration::before { position: absolute; width: 66px; height: 66px; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 50%; content: ''; }
.overview-illustration svg { z-index: 1; width: 30px; opacity: 0.9; }
.overview-illustration span { position: absolute; width: 6px; height: 6px; border-radius: 50%; background: #92ecdd; }
.overview-illustration span:nth-child(2) { top: 11px; right: 17px; }
.overview-illustration span:nth-child(3) { bottom: 12px; left: 13px; background: #ffc48c; }
.goal-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 17px; }
.goal-toolbar > span { color: var(--text-muted); font-size: 11px; }
.filter-tabs { display: flex; padding: 4px; border: 1px solid var(--border-light); border-radius: 12px; background: #fff; gap: 2px; }
.filter-tabs button { min-height: 34px; padding: 0 15px; border: 0; border-radius: 8px; color: var(--text-secondary); background: transparent; cursor: pointer; font-size: 11px; font-weight: 700; }
.filter-tabs button.active { color: var(--primary); background: var(--primary-soft); }
.goals-grid { display: grid; gap: 17px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.goal-card { position: relative; display: flex; min-height: 390px; padding: 22px; flex-direction: column; }
.goal-card__top { display: flex; align-items: center; margin-bottom: 18px; gap: 9px; }
.goal-icon { display: grid; width: 42px; height: 42px; margin-right: auto; place-items: center; border-radius: 13px; }
.goal-icon svg { width: 20px; }
.more-button { display: grid; width: 30px; height: 30px; padding: 0; place-items: center; border: 0; border-radius: 8px; color: var(--text-muted); background: transparent; cursor: pointer; }
.more-button:hover { color: var(--primary); background: var(--primary-soft); }
.more-button svg { width: 18px; }
.goal-category { color: var(--primary); font-size: 9px; font-weight: 800; letter-spacing: 0.1em; }
.goal-card h2 { margin: 6px 0 9px; color: var(--text-strong); font-size: 17px; line-height: 1.45; }
.goal-card > p { min-height: 43px; margin: 0 0 14px; color: var(--text-secondary); font-size: 11px; line-height: 1.7; }
.goal-progress { margin-top: auto; }
.goal-progress > div { display: flex; justify-content: space-between; margin-bottom: 8px; color: var(--text-muted); font-size: 10px; }
.goal-progress strong { color: var(--text-strong); font-size: 12px; }
.goal-meta { display: flex; align-items: center; padding: 13px 0; margin-top: 10px; border-top: 1px solid #f0f1f5; color: var(--text-muted); font-size: 9px; gap: 10px; }
.goal-meta span { display: inline-flex; align-items: center; gap: 4px; }
.goal-meta span:nth-child(2) { margin-left: auto; }
.goal-meta svg { width: 12px; }
.goal-meta .overdue { color: var(--danger); }
.manage-tasks-button { display: flex; min-height: 36px; align-items: center; justify-content: center; border: 1px solid #e6e7f0; border-radius: 9px; color: var(--text-secondary); background: #fafafd; cursor: pointer; font-size: 10px; font-weight: 750; gap: 6px; }
.manage-tasks-button:hover { color: var(--primary); border-color: #d9daf4; background: var(--primary-soft); }
.manage-tasks-button svg { width: 14px; }
.create-goal-card { display: flex; min-height: 390px; align-items: center; justify-content: center; border: 1.5px dashed #d9dbe8; border-radius: 18px; color: var(--text-secondary); background: rgba(255, 255, 255, 0.42); cursor: pointer; flex-direction: column; }
.create-goal-card:hover { color: var(--primary); border-color: #bcbdef; background: #f8f8ff; }
.create-goal-card > span { display: grid; width: 50px; height: 50px; margin-bottom: 14px; place-items: center; border-radius: 16px; color: var(--primary); background: var(--primary-soft); }
.create-goal-card svg { width: 22px; }
.create-goal-card strong { font-size: 13px; }
.create-goal-card small { margin-top: 4px; color: var(--text-muted); font-size: 9px; }
.form-row { display: grid; gap: 15px; grid-template-columns: 1fr 1fr; }
.form-row :deep(.el-select), :deep(.el-date-editor) { width: 100%; }
.color-picker { display: flex; gap: 10px; }
.color-picker button { display: grid; width: 29px; height: 29px; padding: 0; place-items: center; border: 3px solid #fff; border-radius: 9px; box-shadow: 0 0 0 1px #dddfea; cursor: pointer; }
.color-picker button.selected { box-shadow: 0 0 0 2px var(--primary); }
.color-picker svg { width: 13px; color: #fff; }
.task-editor__form { display: grid; align-items: center; gap: 8px; grid-template-columns: minmax(180px, 1fr) 155px 125px auto auto; }
.task-editor__form :deep(.el-input-number) { width: 125px; }
.task-editor__hint { margin: 8px 0 18px; color: var(--text-muted); font-size: 9px; }
.managed-task-list { max-height: 360px; overflow-y: auto; border-top: 1px solid var(--border-light); }
.managed-task-list article { display: flex; align-items: center; padding: 13px 5px; border-bottom: 1px solid var(--border-light); gap: 9px; }
.managed-task-list article > div { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.managed-task-list strong { overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.managed-task-list small { margin-top: 3px; color: var(--text-muted); font-size: 9px; }
.managed-task-list article.done strong { color: var(--text-muted); text-decoration: line-through; }

@media (max-width: 1200px) { .goals-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 720px) {
  .goal-overview { padding: 20px; gap: 16px; }
  .overview-illustration { display: none; }
  .goal-toolbar { align-items: stretch; flex-direction: column; gap: 9px; }
  .filter-tabs { overflow-x: auto; }
  .filter-tabs button { flex: 1; white-space: nowrap; }
  .goals-grid { grid-template-columns: 1fr; }
  .goal-card, .create-goal-card { min-height: 365px; }
  .form-row { grid-template-columns: 1fr; gap: 0; }
  .task-editor__form { grid-template-columns: 1fr 1fr; }
  .task-editor__form > :first-child { grid-column: 1 / -1; }
  .task-editor__form :deep(.el-input-number) { width: 100%; }
}
</style>

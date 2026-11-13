import dayjs from 'dayjs'
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import { initialCheckins, initialGoals } from '@/mocks/data'
import { ApiError } from '@/services/httpClient'
import {
  studyDataApi,
  type CheckinWritePayload,
  type GoalWritePayload,
  type TaskWritePayload,
} from '@/services/studyData'
import type { Checkin, GoalTask, StudyGoal, WeeklyStudyPoint } from '@/types/models'
import { createId, loadStored, saveStored, STORAGE_KEYS } from '@/utils/storage'

interface StudyState {
  goals: StudyGoal[]
  checkins: Checkin[]
}

type MaybePromise<T> = T | Promise<T>

const fallback: StudyState = { goals: initialGoals, checkins: initialCheckins }
const apiMode = import.meta.env.MODE !== 'test' && import.meta.env.VITE_BUSINESS_DATA_MODE !== 'mock'

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : '学习数据加载失败，请稍后重试'
}

function goalPayload(goal: Omit<StudyGoal, 'id' | 'createdAt' | 'tasks'>): GoalWritePayload {
  return {
    title: goal.title,
    description: goal.description,
    category: goal.category,
    tags: goal.tags,
    startDate: goal.startDate,
    targetDate: goal.targetDate,
    status: goal.status,
    color: goal.color,
  }
}

export const useStudyStore = defineStore('study', () => {
  const stored = apiMode ? { goals: [], checkins: [] } : loadStored(STORAGE_KEYS.study, fallback)
  const goals = ref<StudyGoal[]>(stored.goals)
  const checkins = ref<Checkin[]>(stored.checkins)
  const loading = ref(false)
  const initialized = ref(false)
  const error = ref('')
  let generation = 0

  watch(
    [goals, checkins],
    () => {
      if (!apiMode) saveStored(STORAGE_KEYS.study, { goals: goals.value, checkins: checkins.value })
    },
    { deep: true },
  )

  const activeGoals = computed(() => goals.value.filter((goal) => goal.status === '进行中'))
  const today = computed(() => dayjs().format('YYYY-MM-DD'))
  const todayTasks = computed(() =>
    activeGoals.value.flatMap((goal) =>
      goal.tasks
        .filter((task) => task.dueDate === today.value)
        .map((task) => ({ ...task, goalId: goal.id, goalTitle: goal.title, goalColor: goal.color })),
    ),
  )
  const totalMinutes = computed(() => checkins.value.reduce((sum, item) => sum + item.duration, 0))
  const totalCompletedTasks = computed(() =>
    goals.value.reduce((sum, goal) => sum + goal.tasks.filter((task) => task.completed).length, 0),
  )
  const streakDays = computed(() => {
    const dates = new Set(checkins.value.map((item) => item.date))
    let cursor = dates.has(dayjs().format('YYYY-MM-DD')) ? dayjs() : dayjs().subtract(1, 'day')
    let streak = 0
    while (dates.has(cursor.format('YYYY-MM-DD'))) {
      streak += 1
      cursor = cursor.subtract(1, 'day')
    }
    return streak
  })
  const weeklyMinutes = computed(() => {
    const start = dayjs().startOf('week').add(1, 'day')
    const end = start.add(6, 'day')
    return checkins.value
      .filter((item) => {
        const current = dayjs(item.date)
        return !current.isBefore(start, 'day') && !current.isAfter(end, 'day')
      })
      .reduce((sum, item) => sum + item.duration, 0)
  })
  const weeklySeries = computed<WeeklyStudyPoint[]>(() => {
    const labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    const start = dayjs().startOf('week').add(1, 'day')
    return labels.map((label, index) => {
      const current = start.add(index, 'day').format('YYYY-MM-DD')
      return {
        label,
        date: current,
        minutes: checkins.value
          .filter((item) => item.date === current)
          .reduce((sum, item) => sum + item.duration, 0),
      }
    })
  })

  async function initialize(force = false): Promise<void> {
    if (!apiMode || (initialized.value && !force) || loading.value) return
    loading.value = true
    error.value = ''
    const currentGeneration = generation
    try {
      const [remoteGoals, remoteCheckins] = await Promise.all([
        studyDataApi.getGoals(),
        studyDataApi.getCheckins(),
      ])
      if (currentGeneration !== generation) return
      goals.value = remoteGoals
      checkins.value = remoteCheckins
      initialized.value = true
    } catch (cause) {
      if (currentGeneration === generation) error.value = errorMessage(cause)
      throw cause
    } finally {
      if (currentGeneration === generation) loading.value = false
    }
  }

  function goalProgress(goal: StudyGoal): number {
    if (goal.tasks.length === 0) return 0
    return Math.round((goal.tasks.filter((task) => task.completed).length / goal.tasks.length) * 100)
  }

  function addGoal(goal: Omit<StudyGoal, 'id' | 'createdAt'>): MaybePromise<string> {
    if (apiMode) {
      const currentGeneration = generation
      return studyDataApi.createGoal(goalPayload(goal)).then((created) => {
        if (currentGeneration === generation) goals.value.unshift(created)
        return created.id
      })
    }
    const id = createId('goal')
    goals.value.unshift({ ...structuredClone(goal), id, createdAt: new Date().toISOString() })
    return id
  }

  function updateGoal(
    id: string,
    patch: Partial<Omit<StudyGoal, 'id' | 'createdAt'>>,
  ): MaybePromise<void> {
    const current = goals.value.find((item) => item.id === id)
    if (!current) return
    if (apiMode) {
      const merged = { ...current, ...structuredClone(patch) }
      const currentGeneration = generation
      return studyDataApi.updateGoal(id, goalPayload(merged)).then((updated) => {
        if (currentGeneration !== generation) return
        const index = goals.value.findIndex((item) => item.id === id)
        if (index >= 0) goals.value[index] = updated
      })
    }
    Object.assign(current, structuredClone(patch))
  }

  function removeGoal(id: string): MaybePromise<void> {
    if (apiMode) {
      const currentGeneration = generation
      return studyDataApi.deleteGoal(id).then(() => {
        if (currentGeneration !== generation) return
        goals.value = goals.value.filter((goal) => goal.id !== id)
      })
    }
    goals.value = goals.value.filter((goal) => goal.id !== id)
  }

  function updateTaskRemote(goalId: string, task: GoalTask): Promise<void> {
    const currentGeneration = generation
    const payload: TaskWritePayload = {
      title: task.title,
      dueDate: task.dueDate,
      estimatedMinutes: task.estimatedMinutes,
      completed: task.completed,
    }
    return studyDataApi.updateTask(goalId, task.id, payload).then((updated) => {
      if (currentGeneration !== generation) return
      const goal = goals.value.find((item) => item.id === goalId)
      const index = goal?.tasks.findIndex((item) => item.id === updated.id) ?? -1
      if (goal && index >= 0) goal.tasks[index] = updated
    })
  }

  function toggleTask(goalId: string, taskId: string): MaybePromise<void> {
    const task = goals.value.find((goal) => goal.id === goalId)?.tasks.find((item) => item.id === taskId)
    if (!task) return
    if (apiMode) return updateTaskRemote(goalId, { ...task, completed: !task.completed })
    task.completed = !task.completed
  }

  function addTask(goalId: string, task: Omit<GoalTask, 'id'>): MaybePromise<void> {
    const currentGeneration = generation
    const goal = goals.value.find((item) => item.id === goalId)
    if (!goal) return
    if (apiMode) {
      return studyDataApi.createTask(goalId, task).then((created) => {
        if (currentGeneration !== generation) return
        goal.tasks.push(created)
      })
    }
    goal.tasks.push({ ...task, id: createId('task') })
  }

  function updateTask(
    goalId: string,
    taskId: string,
    patch: Partial<Omit<GoalTask, 'id'>>,
  ): MaybePromise<void> {
    const task = goals.value.find((goal) => goal.id === goalId)?.tasks.find((item) => item.id === taskId)
    if (!task) return
    if (apiMode) return updateTaskRemote(goalId, { ...task, ...patch })
    Object.assign(task, patch)
  }

  function removeTask(goalId: string, taskId: string): MaybePromise<void> {
    const currentGeneration = generation
    const goal = goals.value.find((item) => item.id === goalId)
    if (!goal) return
    if (apiMode) {
      return studyDataApi.deleteTask(goalId, taskId).then(() => {
        if (currentGeneration !== generation) return
        goal.tasks = goal.tasks.filter((task) => task.id !== taskId)
      })
    }
    goal.tasks = goal.tasks.filter((task) => task.id !== taskId)
  }

  function addCheckin(checkin: CheckinWritePayload): MaybePromise<void> {
    if (apiMode) {
      const currentGeneration = generation
      return studyDataApi.createCheckin(checkin).then((created) => {
        if (currentGeneration === generation) checkins.value.unshift(created)
      })
    }
    checkins.value.unshift({
      ...structuredClone(checkin),
      id: createId('checkin'),
      createdAt: new Date().toISOString(),
    })
  }

  function resetStudyData(): MaybePromise<void> {
    if (apiMode) return initialize(true)
    goals.value = structuredClone(initialGoals)
    checkins.value = structuredClone(initialCheckins)
  }

  function clearAccountData(): void {
    if (!apiMode) return
    generation += 1
    goals.value = []
    checkins.value = []
    initialized.value = false
    loading.value = false
    error.value = ''
  }

  return {
    apiMode,
    goals,
    checkins,
    loading,
    initialized,
    error,
    activeGoals,
    todayTasks,
    totalMinutes,
    totalCompletedTasks,
    streakDays,
    weeklyMinutes,
    weeklySeries,
    initialize,
    goalProgress,
    addGoal,
    updateGoal,
    removeGoal,
    toggleTask,
    addTask,
    updateTask,
    removeTask,
    addCheckin,
    resetStudyData,
    clearAccountData,
  }
})

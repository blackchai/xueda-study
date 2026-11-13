import { request, requestNoContent } from '@/services/httpClient'
import type { Checkin, GoalTask, StudyGoal } from '@/types/models'

export type GoalWritePayload = Omit<StudyGoal, 'id' | 'createdAt' | 'tasks'>
export type TaskWritePayload = Omit<GoalTask, 'id'>
export type CheckinWritePayload = Omit<Checkin, 'id' | 'createdAt'>

export const studyDataApi = {
  async getGoals(): Promise<StudyGoal[]> {
    return (await request<StudyGoal[]>('/goals')).data
  },

  async createGoal(payload: GoalWritePayload): Promise<StudyGoal> {
    return (await request<StudyGoal>('/goals', {
      method: 'POST',
      body: JSON.stringify(payload),
    })).data
  },

  async updateGoal(id: string, payload: GoalWritePayload): Promise<StudyGoal> {
    return (await request<StudyGoal>(`/goals/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })).data
  },

  async deleteGoal(id: string): Promise<void> {
    await requestNoContent(`/goals/${id}`, { method: 'DELETE' })
  },

  async createTask(goalId: string, payload: TaskWritePayload): Promise<GoalTask> {
    return (await request<GoalTask>(`/goals/${goalId}/tasks`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })).data
  },

  async updateTask(goalId: string, taskId: string, payload: TaskWritePayload): Promise<GoalTask> {
    return (await request<GoalTask>(`/goals/${goalId}/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })).data
  },

  async deleteTask(goalId: string, taskId: string): Promise<void> {
    await requestNoContent(`/goals/${goalId}/tasks/${taskId}`, { method: 'DELETE' })
  },

  async getCheckins(): Promise<Checkin[]> {
    return (await request<Checkin[]>('/checkins')).data
  },

  async createCheckin(payload: CheckinWritePayload): Promise<Checkin> {
    return (await request<Checkin>('/checkins', {
      method: 'POST',
      body: JSON.stringify(payload),
    })).data
  },
}

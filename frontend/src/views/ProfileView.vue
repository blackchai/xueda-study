<script setup lang="ts">
import { Bell, Clock, Delete, Edit, Lock, Plus, Refresh, User } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import PageHeader from '@/components/PageHeader.vue'
import { getAuthenticatedUser, logoutAuthenticatedUser } from '@/services/authSession'
import { useProfileStore } from '@/stores/profile'
import { useStudyStore } from '@/stores/study'
import {
  GOAL_CATEGORIES,
  STUDY_STAGES,
  STUDY_STYLES,
  type DayOfWeek,
  type StudyTimeSlot,
  type UserProfile,
} from '@/types/models'
import type { AuthenticatedUser } from '@/types/api'
import { cloneValue, createId } from '@/utils/storage'

const router = useRouter()
const profileStore = useProfileStore()
const studyStore = useStudyStore()
const editing = ref(false)
const account = ref<AuthenticatedUser>()
const form = ref<UserProfile>(cloneValue(profileStore.profile))
const displayName = computed(() => profileStore.initialized ? profileStore.profile.name : account.value?.displayName ?? '同学')
const displayAvatar = computed(() => displayName.value.trim().slice(0, 1) || '学')

async function loadProfile(): Promise<void> {
  try {
    const [user] = await Promise.all([getAuthenticatedUser(), profileStore.initialize(true)])
    account.value = user
    form.value = cloneValue(profileStore.profile)
  } catch {
    ElMessage.error(profileStore.error || '学习档案加载失败，请重试')
  }
}

onMounted(() => { void loadProfile() })

const dayOptions: Array<{ value: DayOfWeek; label: string }> = [
  { value: 1, label: '周一' }, { value: 2, label: '周二' }, { value: 3, label: '周三' },
  { value: 4, label: '周四' }, { value: 5, label: '周五' }, { value: 6, label: '周六' }, { value: 7, label: '周日' },
]

function startEditing(): void {
  form.value = cloneValue(profileStore.profile)
  editing.value = true
}

function cancelEditing(): void {
  form.value = cloneValue(profileStore.profile)
  editing.value = false
}

async function saveProfile(): Promise<void> {
  if (!form.value.name.trim()) {
    ElMessage.warning('昵称不能为空')
    return
  }
  if (form.value.timeSlots.some((slot) => !slot.start || !slot.end || slot.end <= slot.start)) {
    ElMessage.warning('结束时间须晚于开始时间；跨午夜请拆成两天')
    return
  }
  try {
    await profileStore.updateProfile(form.value)
    form.value = cloneValue(profileStore.profile)
    editing.value = false
    ElMessage.success(profileStore.apiMode ? '学习档案已保存，刷新推荐即可使用新偏好' : 'Mock 偏好已保存到当前浏览器')
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '保存失败，请重试')
  }
}

function addTimeSlot(): void {
  const lastDay = form.value.timeSlots.at(-1)?.day ?? 1
  form.value.timeSlots.push({ id: createId('slot'), day: lastDay, start: '19:00', end: '21:00' })
}

function removeTimeSlot(id: string): void {
  form.value.timeSlots = form.value.timeSlots.filter((slot) => slot.id !== id)
}

function slotDayLabel(slot: StudyTimeSlot): string {
  return dayOptions.find((day) => day.value === slot.day)?.label ?? `周${slot.day}`
}

async function resetPrototype(): Promise<void> {
  if (studyStore.apiMode) return
  try {
    await ElMessageBox.confirm(
      '将恢复当前浏览器的目标、打卡与偏好演示数据。真实小组数据不受影响。',
      '重置开发演示数据',
      { confirmButtonText: '确认重置', cancelButtonText: '取消', type: 'warning' },
    )
    if (!profileStore.apiMode) profileStore.resetProfile()
    await studyStore.resetStudyData()
    form.value = cloneValue(profileStore.profile)
    ElMessage.success('开发演示数据已恢复')
  } catch {
    // User cancelled.
  }
}

async function exitPrototype(): Promise<void> {
  try {
    await logoutAuthenticatedUser()
    profileStore.clearAccountData()
    studyStore.clearAccountData()
    ElMessage.success('已安全退出登录')
    await router.push('/auth')
  } catch {
    ElMessage.error('退出登录失败，请稍后重试')
  }
}
</script>

<template>
  <div class="profile-view">
    <PageHeader eyebrow="MY PROFILE" title="个人中心" description="完善真实的学习方向、作息和偏好，才能得到更有意义的目标反馈与搭子推荐。">
      <template #actions>
        <el-button v-if="!editing" type="primary" :icon="Edit" :disabled="profileStore.loading || !!profileStore.error" @click="startEditing">编辑资料</el-button>
        <template v-else>
          <el-button :disabled="profileStore.saving" @click="cancelEditing">取消</el-button>
          <el-button type="primary" :loading="profileStore.saving" @click="saveProfile">保存修改</el-button>
        </template>
      </template>
    </PageHeader>

    <el-alert v-if="profileStore.error" :title="profileStore.error" type="error" :closable="false" show-icon>
      <template #default><el-button link type="primary" @click="loadProfile">重试加载</el-button></template>
    </el-alert>
    <el-alert v-if="!profileStore.apiMode" title="Mock 演示模式：本页偏好仅保存到当前浏览器。" type="info" :closable="false" />

    <section class="profile-hero">
      <span class="profile-avatar">{{ displayAvatar }}</span>
      <div class="profile-identity">
        <div><h2>{{ displayName }}</h2><el-tag type="success" effect="light">真实账号已登录</el-tag></div>
        <p>{{ account?.username ? `@${account.username}` : '' }}{{ account?.email ? ` · ${account.email}` : '' }}</p>
        <span>{{ profileStore.profile.bio }}</span>
      </div>
      <div class="profile-quick-stats">
        <div><strong>{{ studyStore.streakDays }}</strong><small>连续打卡</small></div>
        <div><strong>{{ Math.round(studyStore.totalMinutes / 60) }}</strong><small>累计小时</small></div>
        <div><strong>{{ studyStore.activeGoals.length }}</strong><small>进行中目标</small></div>
      </div>
    </section>

    <div v-if="editing" class="editing-notice"><Edit /> 正在编辑个人档案。保存后，搭子匹配分会根据新偏好即时重新计算。</div>

    <div v-loading="profileStore.loading" class="profile-grid" element-loading-text="正在加载学习档案">
      <div class="profile-main">
        <section class="settings-card surface-card">
          <div class="section-title"><div><h2><User /> 基本资料</h2><p>推荐只展示昵称；学校、专业和简介仅自己可见</p></div></div>
          <div class="settings-form two-columns">
            <label><span>公开昵称</span><el-input v-model="form.name" :disabled="!editing" maxlength="50" placeholder="建议使用昵称，不填写真实姓名" /></label>
            <label><span>学校（仅自己可见）</span><el-input v-model="form.school" :disabled="!editing" maxlength="100" /></label>
            <label><span>专业（仅自己可见）</span><el-input v-model="form.major" :disabled="!editing" maxlength="100" /></label>
            <label class="full"><span>个人简介</span><el-input v-model="form.bio" :disabled="!editing" type="textarea" :rows="3" maxlength="120" show-word-limit /></label>
          </div>
        </section>

        <section class="settings-card surface-card">
          <div class="section-title"><div><h2><Edit /> 学习方向</h2><p>匹配算法中目标相似度 G 的主要来源</p></div></div>
          <div class="settings-form">
            <label><span>目标分类（可多选）</span>
              <el-select v-model="form.categories" :disabled="!editing" multiple :multiple-limit="8">
                <el-option v-for="category in GOAL_CATEGORIES" :key="category" :label="category" :value="category" />
              </el-select>
            </label>
            <label><span>学习标签</span>
              <el-select v-model="form.tags" :disabled="!editing" multiple :multiple-limit="20" filterable allow-create default-first-option placeholder="例如 C++、Python；每项最多 32 字">
                <el-option v-for="tag in form.tags" :key="tag" :label="tag" :value="tag" />
              </el-select>
            </label>
            <label><span>当前阶段</span>
              <el-radio-group v-model="form.stage" :disabled="!editing">
                <el-radio-button v-for="stage in STUDY_STAGES" :key="stage" :value="stage">{{ stage }}</el-radio-button>
              </el-radio-group>
            </label>
            <label><span>学习方式（可多选）</span>
              <el-checkbox-group v-model="form.styles" :disabled="!editing" class="style-options">
                <el-checkbox v-for="style in STUDY_STYLES" :key="style" :value="style" border>{{ style }}</el-checkbox>
              </el-checkbox-group>
            </label>
          </div>
        </section>

        <section class="settings-card surface-card">
          <div class="section-title">
            <div><h2><Clock /> 每周可用时间</h2><p>北京时间 UTC+8，按同一天的真实重合分钟数计算；最多 42 个时段</p></div>
            <el-button v-if="editing" size="small" :icon="Plus" :disabled="form.timeSlots.length >= 42" @click="addTimeSlot">添加时段</el-button>
          </div>
          <div v-if="editing" class="time-slot-editor">
            <div v-for="slot in form.timeSlots" :key="slot.id">
              <el-select v-model="slot.day" aria-label="星期">
                <el-option v-for="day in dayOptions" :key="day.value" :label="day.label" :value="day.value" />
              </el-select>
              <el-time-select v-model="slot.start" start="00:00" step="00:15" end="23:45" placeholder="开始" aria-label="开始时间" />
              <span>至</span>
              <el-time-select v-model="slot.end" start="00:15" step="00:15" end="24:00" placeholder="结束" aria-label="结束时间" />
              <el-button circle text type="danger" :icon="Delete" aria-label="删除时段" @click="removeTimeSlot(slot.id)" />
            </div>
            <p v-if="form.timeSlots.length === 0">尚未设置时段，时间重合度会按 50 分中性值计算。</p>
          </div>
          <div v-else class="time-slot-display">
            <span v-for="slot in profileStore.profile.timeSlots" :key="slot.id"><strong>{{ slotDayLabel(slot) }}</strong>{{ slot.start }}—{{ slot.end }}</span>
            <p v-if="profileStore.profile.timeSlots.length === 0">暂未设置学习时段</p>
          </div>
        </section>
      </div>

      <aside class="profile-side">
        <section class="settings-card surface-card">
          <div class="section-title"><div><h2><Bell /> 匹配与隐私</h2><p>只有本人主动开启后，才会出现在他人推荐中</p></div></div>
          <div class="preference-list">
            <label><span><strong>允许被推荐</strong><small>公开昵称、学习方向、标签、方式、阶段和可用时段</small></span><el-switch v-model="form.publicProfile" aria-label="允许被推荐" :disabled="!editing" /></label>
            <label><span><strong>接收搭子邀请</strong><small>与“允许被推荐”同时开启后，可收到新申请；关闭不影响已有申请和关系</small></span><el-switch v-model="form.allowInvites" aria-label="接收搭子邀请" :disabled="!editing" /></label>
            <label><span><strong>打卡提醒</strong><small>尚未开放</small></span><el-switch :model-value="false" disabled /></label>
          </div>
          <p class="privacy-note">发送邀请及建立搭子关系会向对方分享匹配档案。解除关系且不再公开后，对方无法继续查看这些资料。</p>
          <label class="daily-target"><span>每日目标时长</span><el-input-number v-model="form.dailyTargetMinutes" :disabled="!editing" :min="30" :max="720" :step="30" /><small>分钟</small></label>
        </section>

        <section class="account-card surface-card">
          <span class="account-card__icon"><Lock /></span>
          <h2>账号与安全</h2>
          <p>当前使用用户名或邮箱安全登录，会话令牌仅保存在 HttpOnly Cookie 中。</p>
          <p v-if="account?.email">{{ account.username }} · {{ account.email }}</p>
          <el-button @click="exitPrototype">退出登录</el-button>
        </section>

        <section class="data-card surface-card">
          <h2>{{ studyStore.apiMode ? '数据与隐私' : '个人学习演示' }}</h2>
          <p>真实模式下，档案、目标、打卡、搭子与小组均通过服务端持久化。个人打卡默认私有，只有主动分享的部分对所选小组成员可见。</p>
          <p v-if="!studyStore.apiMode">当前个人目标与打卡为本地演示；小组始终连接真实账号 API。</p>
          <el-button v-if="!studyStore.apiMode" :icon="Refresh" @click="resetPrototype">重置个人演示数据</el-button>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.profile-hero { display: grid; align-items: center; padding: 27px 30px; margin-bottom: 18px; border: 1px solid #e3e4f7; border-radius: 20px; background: linear-gradient(135deg, #f8f8ff, #f0f4ff); gap: 20px; grid-template-columns: auto 1fr auto; }
.profile-avatar { display: grid; width: 84px; height: 84px; place-items: center; border: 5px solid #fff; border-radius: 25px; color: #fff; background: linear-gradient(145deg, #7772ec, #4f51cc); box-shadow: 0 13px 30px rgba(91, 92, 226, 0.22); font-size: 28px; font-weight: 900; }
.profile-identity > div { display: flex; align-items: center; gap: 10px; }
.profile-identity h2 { margin: 0; font-size: 22px; }
.profile-identity p { margin: 5px 0; color: var(--text-secondary); font-size: 10px; }
.profile-identity > span { color: var(--text-muted); font-size: 9px; line-height: 1.6; }
.profile-quick-stats { display: grid; min-width: 290px; padding-left: 25px; border-left: 1px solid #dddff0; grid-template-columns: repeat(3, 1fr); }
.profile-quick-stats div { display: flex; align-items: center; flex-direction: column; }
.profile-quick-stats strong { color: var(--primary); font-size: 23px; }
.profile-quick-stats small { color: var(--text-muted); font-size: 8px; }
.editing-notice { display: flex; align-items: center; padding: 11px 14px; margin-bottom: 16px; border: 1px solid #e1e2fb; border-radius: 11px; color: var(--primary-dark); background: #f5f5ff; font-size: 10px; gap: 7px; }
.editing-notice svg { width: 14px; }
.profile-grid { display: grid; align-items: start; gap: 18px; grid-template-columns: minmax(0, 1.55fr) minmax(300px, 0.65fr); }
.profile-main, .profile-side { display: flex; gap: 18px; flex-direction: column; }
.settings-card, .account-card, .data-card { padding: 23px; }
.section-title h2 { display: flex; align-items: center; gap: 7px; }
.section-title h2 svg { width: 17px; color: var(--primary); }
.settings-form { display: grid; gap: 15px; }
.settings-form.two-columns { grid-template-columns: 1fr 1fr; }
.settings-form label { display: flex; gap: 6px; flex-direction: column; }
.settings-form label.full { grid-column: 1 / -1; }
.settings-form label > span, .daily-target > span { color: var(--text-secondary); font-size: 10px; font-weight: 700; }
.settings-form :deep(.el-select) { width: 100%; }
.style-options { display: grid; gap: 7px; grid-template-columns: repeat(3, 1fr); }
.style-options :deep(.el-checkbox) { margin-right: 0; }
.time-slot-editor { display: flex; gap: 8px; flex-direction: column; }
.time-slot-editor > div { display: grid; align-items: center; gap: 8px; grid-template-columns: 100px 1fr auto 1fr auto; }
.time-slot-editor > p, .time-slot-display > p { color: var(--text-muted); font-size: 9px; }
.time-slot-display { display: grid; gap: 8px; grid-template-columns: repeat(3, 1fr); }
.time-slot-display > span { display: flex; padding: 10px 12px; border-radius: 10px; color: var(--text-secondary); background: #f5f6fa; font-size: 9px; flex-direction: column; }
.time-slot-display strong { margin-bottom: 3px; color: var(--text-strong); font-size: 10px; }
.preference-list { display: flex; flex-direction: column; }
.preference-list label { display: flex; align-items: center; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid var(--border-light); gap: 12px; }
.preference-list label > span { display: flex; flex-direction: column; }
.preference-list strong { font-size: 10px; }
.preference-list small { margin-top: 3px; color: var(--text-muted); font-size: 7px; }
.privacy-note { color: var(--text-secondary); font-size: 12px; line-height: 1.7; }
.daily-target { display: flex; align-items: center; padding-top: 17px; gap: 8px; }
.daily-target > span { flex: 1; }
.daily-target small { color: var(--text-muted); font-size: 8px; }
.account-card { text-align: center; }
.account-card__icon { display: grid; width: 47px; height: 47px; margin: 0 auto 12px; place-items: center; border-radius: 15px; color: var(--primary); background: var(--primary-soft); }
.account-card__icon svg { width: 21px; }
.account-card h2, .data-card h2 { margin: 0; font-size: 14px; }
.account-card p, .data-card p { color: var(--text-secondary); font-size: 9px; line-height: 1.7; }
.data-card :deep(.el-button) { width: 100%; margin: 8px 0 0; }

@media (max-width: 1100px) {
  .profile-grid { grid-template-columns: 1fr; }
  .profile-side { display: grid; align-items: stretch; grid-template-columns: repeat(2, 1fr); }
  .profile-side .settings-card { grid-column: 1 / -1; }
}

@media (max-width: 700px) {
  .profile-hero { align-items: center; padding: 22px; grid-template-columns: auto 1fr; }
  .profile-avatar { width: 65px; height: 65px; border-radius: 20px; }
  .profile-quick-stats { grid-column: 1 / -1; min-width: 0; padding: 16px 0 0; border-top: 1px solid #dddff0; border-left: 0; }
  .profile-identity > div { align-items: flex-start; flex-direction: column; gap: 4px; }
  .settings-card, .account-card, .data-card { padding: 18px; }
  .settings-form.two-columns { grid-template-columns: 1fr; }
  .settings-form label.full { grid-column: auto; }
  .style-options { grid-template-columns: repeat(2, 1fr); }
  .time-slot-editor > div { grid-template-columns: 1fr 1fr auto; }
  .time-slot-editor > div > span { display: none; }
  .time-slot-editor > div > :nth-child(1) { grid-column: 1 / -1; }
  .time-slot-display { grid-template-columns: repeat(2, 1fr); }
  .profile-side { display: flex; }
}
</style>

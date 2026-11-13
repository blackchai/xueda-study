<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import EmptyState from './EmptyState.vue'
import PublicStudyProfile from './PublicStudyProfile.vue'
import NotificationList from './NotificationList.vue'
import { buddyConnectionsApi } from '@/services/buddyConnections'
import { ApiError } from '@/services/httpClient'
import type { BuddyInvitation, BuddyRelation, ConnectionTab, InvitationAction, InvitationStatus } from '@/types/buddies'
import type { PublicBuddyProfile } from '@/types/matching'

const props = defineProps<{ tab: ConnectionTab }>()
const emit = defineEmits<{
  changed: []
  unreadChange: [count: number]
  navigate: [tab: ConnectionTab]
}>()
const loading = ref(false)
const error = ref('')
const busyId = ref('')
const page = ref(1)
const pageSize = 12
const total = ref(0)
const status = ref<InvitationStatus>()
const invitations = ref<BuddyInvitation[]>([])
const relations = ref<BuddyRelation[]>([])
const notificationPanel = ref<InstanceType<typeof NotificationList>>()
const selectedProfile = ref<PublicBuddyProfile>()
const drawerOpen = ref(false)
let sequence = 0
const titles: Record<ConnectionTab, string> = { incoming: '收到的邀请', outgoing: '已发送邀请', mine: '我的搭子', notifications: '站内通知' }
const title = computed(() => titles[props.tab])
const statusNames: Record<InvitationStatus, string> = { pending: '等待接受', accepted: '已接受', rejected: '已拒绝', cancelled: '已取消' }

async function load(): Promise<void> {
  if (props.tab === 'notifications') { await notificationPanel.value?.refresh(); return }
  const ticket = ++sequence
  loading.value = true
  error.value = ''
  invitations.value = []
  relations.value = []
  try {
    const options = { page: page.value, pageSize }
    if (props.tab === 'mine') {
      const result = await buddyConnectionsApi.getBuddies(options)
      if (ticket !== sequence) return
      relations.value = result.items
      total.value = result.total
    } else {
      const result = await buddyConnectionsApi.getInvitations({ ...options, direction: props.tab, status: status.value })
      if (ticket !== sequence) return
      invitations.value = result.items
      total.value = result.total
    }
    const lastPage = Math.max(1, Math.ceil(total.value / pageSize))
    if (page.value > lastPage) { page.value = lastPage; await load() }
  } catch (cause) {
    if (ticket === sequence) error.value = cause instanceof Error ? cause.message : '加载失败，请稍后重试'
  } finally {
    if (ticket === sequence) loading.value = false
  }
}

async function action(id: string, operation: () => Promise<unknown>, message: string): Promise<void> {
  if (busyId.value) return
  busyId.value = id
  try {
    await operation()
    ElMessage.success(message)
    await load()
    emit('changed')
  } catch (cause) {
    if (cause !== 'cancel' && cause !== 'close') {
      ElMessage.error(cause instanceof Error ? cause.message : '操作失败，请稍后重试')
      if (cause instanceof ApiError && (cause.status === 409 || cause.status === 404)) await load()
    }
  } finally {
    busyId.value = ''
  }
}

function resolve(item: BuddyInvitation, next: InvitationAction): void {
  const messages = { accept: '已建立学习搭子关系', reject: '已拒绝邀请', cancel: '已取消邀请' }
  void action(item.id, () => buddyConnectionsApi.resolveInvitation(item.id, next), messages[next])
}

function unlink(item: BuddyRelation): void {
  void action(item.id, async () => {
    await ElMessageBox.confirm(`确认解除与 ${item.peer.name} 的学习搭子关系？双方的私人目标与打卡不会被删除。`, '解除搭子关系', {
      confirmButtonText: '确认解除', cancelButtonText: '保留关系', type: 'warning',
    })
    await buddyConnectionsApi.removeBuddy(item.id)
  }, '搭子关系已解除')
}

function details(profile: PublicBuddyProfile): void {
  selectedProfile.value = profile
  drawerOpen.value = true
}

function changePage(value: number): void { page.value = value; void load() }
watch(() => props.tab, () => { page.value = 1; status.value = undefined; drawerOpen.value = false; void load() }, { immediate: true })
onBeforeUnmount(() => { sequence += 1 })
defineExpose({ refresh: load })
</script>

<template>
  <NotificationList v-if="tab === 'notifications'" ref="notificationPanel" />
  <section v-else class="connection-panel surface-card" :aria-label="title">
    <div class="connection-heading">
      <div><h2>{{ title }}</h2><p>共 {{ total }} 条 · 账号间状态通过服务端同步</p></div>
      <div class="panel-tools">
        <el-select v-if="tab === 'incoming' || tab === 'outgoing'" v-model="status" placeholder="全部状态" aria-label="邀请状态筛选" clearable @change="page = 1; load()">
          <el-option v-for="(label, value) in statusNames" :key="value" :label="label" :value="value" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新列表</el-button>
      </div>
    </div>
    <el-alert v-if="error" type="error" :title="error" :closable="false" show-icon>
      <template #default><el-button link type="primary" @click="load">重试</el-button></template>
    </el-alert>
    <el-skeleton v-else-if="loading" :rows="5" animated />
    <template v-else>
      <div v-if="invitations.length" class="connection-list">
        <article v-for="item in invitations" :key="item.id" :data-request-id="item.id" class="connection-item">
          <span class="avatar">{{ item.peer.avatar }}</span>
          <div class="item-copy">
            <strong>{{ item.peer.name }}</strong>
            <p>{{ item.message || '期待与你一起学习' }}</p>
            <small>{{ dayjs(item.createdAt).format('YYYY-MM-DD HH:mm') }} · {{ item.peer.categories.join('、') || '匹配档案未公开' }}</small>
          </div>
          <div class="item-actions">
            <el-tag :type="item.status === 'accepted' ? 'success' : item.status === 'pending' ? 'warning' : 'info'">
              {{ item.status === 'accepted' && item.connection.status === 'connected' ? '已成为搭子' : statusNames[item.status] }}
            </el-tag>
            <el-button @click="details(item.peer)">公开资料</el-button>
            <template v-if="item.status === 'pending'">
              <el-button v-if="tab === 'outgoing'" :loading="busyId === item.id" :disabled="!!busyId" @click="resolve(item, 'cancel')">取消邀请</el-button>
              <template v-else>
                <el-button :disabled="!!busyId" @click="resolve(item, 'reject')">拒绝</el-button>
                <el-button type="primary" :loading="busyId === item.id" :disabled="!!busyId" @click="resolve(item, 'accept')">接受邀请</el-button>
              </template>
            </template>
          </div>
        </article>
      </div>
      <div v-else-if="relations.length" class="connection-list">
        <article v-for="item in relations" :key="item.id" :data-relation-id="item.id" class="connection-item">
          <span class="avatar">{{ item.peer.avatar }}</span>
          <div class="item-copy"><strong>{{ item.peer.name }}</strong><p>{{ item.peer.categories.join('、') }} · {{ item.peer.tags.join('、') }}</p><small>成为搭子：{{ dayjs(item.createdAt).format('YYYY-MM-DD') }}</small></div>
          <div class="item-actions">
            <el-button @click="details(item.peer)">学习目标与计划</el-button>
            <el-button type="danger" plain :loading="busyId === item.id" :disabled="!!busyId" @click="unlink(item)">解除关系</el-button>
          </div>
        </article>
      </div>
      <EmptyState v-else :title="`暂无${title}`" :description="tab === 'mine' ? '接受一条真实邀请后，你们会出现在彼此的搭子列表。' : '数据更新后，点击刷新列表即可查看。'" />
    </template>
    <el-pagination v-if="total > pageSize" class="panel-pagination" :current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="changePage" />
    <el-drawer v-model="drawerOpen" title="公开学习资料" size="min(92vw, 440px)">
      <PublicStudyProfile v-if="selectedProfile" :profile="selectedProfile" />
    </el-drawer>
  </section>
</template>

<style scoped>
.connection-panel { padding: 24px; }
.connection-heading { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; margin-bottom: 22px; }
.connection-heading h2 { margin: 0; font-size: 18px; }
.connection-heading p { margin: 4px 0 0; color: var(--text-muted); font-size: 12px; }
.panel-tools { display: flex; gap: 8px; }
.panel-tools .el-select { width: 130px; }
.connection-item { display: flex; align-items: center; padding: 18px 8px; gap: 14px; border-bottom: 1px solid var(--border-light); }
.connection-item:last-child { border-bottom: 0; }
.item-copy { flex: 1; min-width: 0; }
.item-copy strong { overflow-wrap: anywhere; font-size: 14px; }
.item-copy p { margin: 5px 0; color: var(--text-secondary); font-size: 13px; overflow-wrap: anywhere; white-space: pre-wrap; }
.item-copy small { color: var(--text-muted); font-size: 11px; }
.item-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.item-actions .el-button + .el-button { margin-left: 0; }
.notice-dot { width: 9px; height: 9px; flex: 0 0 auto; border-radius: 50%; background: var(--primary); }
.notice-dot.read { background: var(--border-light); }
.is-unread { background: #f8f8ff; }
.panel-pagination { justify-content: center; margin-top: 22px; }
@media (max-width: 760px) {
  .connection-panel { padding: 18px; }
  .connection-item { align-items: flex-start; flex-wrap: wrap; }
  .item-copy { min-width: calc(100% - 62px); }
  .item-actions { width: 100%; justify-content: flex-start; }
  .panel-tools { width: 100%; }
}
</style>

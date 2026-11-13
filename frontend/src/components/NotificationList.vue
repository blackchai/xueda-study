<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import EmptyState from './EmptyState.vue'
import { buddyConnectionsApi } from '@/services/buddyConnections'
import { ApiError } from '@/services/httpClient'
import { useNotificationStore } from '@/stores/notifications'
import type { BuddyNotification } from '@/types/buddies'

const router = useRouter(), store = useNotificationStore()
const items = ref<BuddyNotification[]>([])
const page = ref(1), total = ref(0), unreadOnly = ref(false)
const loading = ref(false), busy = ref(''), error = ref('')
let sequence = 0
async function load(): Promise<void> {
  const ticket = ++sequence
  loading.value = true; error.value = ''; items.value = []
  try {
    const result = await buddyConnectionsApi.getNotifications({ page: page.value, pageSize: 12, unreadOnly: unreadOnly.value })
    if (ticket !== sequence) return
    if (page.value > Math.max(1, Math.ceil(result.total / 12))) { page.value = Math.max(1, Math.ceil(result.total / 12)); return }
    items.value = result.items; total.value = result.total; store.acceptCount(result.unreadCount)
  } catch (cause) {
    if (ticket !== sequence) return
    if (cause instanceof ApiError && cause.status === 401) { store.reset(); store.expired = true }
    error.value = cause instanceof Error ? cause.message : '通知加载失败，请重试'
  } finally { if (ticket === sequence) loading.value = false }
}
async function mark(item?: BuddyNotification): Promise<boolean> {
  if (busy.value) return false
  busy.value = item?.id ?? 'all'
  try {
    if (item && !item.readAt) await buddyConnectionsApi.readNotification(item.id)
    else if (!item) await buddyConnectionsApi.readAllNotifications()
    await load()
    return true
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '标记已读失败')
    return false
  } finally { busy.value = '' }
}
async function navigate(item: BuddyNotification): Promise<void> {
  if (busy.value) return
  if (!item.readAt && !await mark(item)) return
  // Only permit the known business routes, even if a server/proxy is misconfigured.
  if (!/^\/(?:buddies(?:\?tab=(?:incoming|outgoing|mine))?|groups(?:\/[0-9a-f-]+(?:\?tab=requests)?)?)$/.test(item.href)) {
    ElMessage.error('通知关联页面不可用'); return
  }
  await router.push(item.href)
}
const time = (s: string): string => new Date(s).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
watch(page, () => void load())
watch(unreadOnly, () => { if (page.value === 1) void load(); else page.value = 1 })
void load()
onBeforeUnmount(() => { sequence++ })
defineExpose({ refresh: load })
</script>
<template>
  <section class="notification-panel surface-card" aria-label="站内通知列表" :aria-busy="loading">
    <div class="notification-heading"><div><h2>站内通知</h2><p>共 {{ total }} 条 · {{ store.unreadCount }} 条未读</p></div><div class="notice-tools"><el-switch v-model="unreadOnly" aria-label="只看未读通知" active-text="只看未读" /><el-button :icon="Refresh" :loading="loading" :disabled="!!busy" @click="load">刷新通知</el-button><el-button :loading="busy === 'all'" :disabled="!!busy || loading || !store.unreadCount" @click="mark()">全部标为已读</el-button></div></div>
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false"><el-button link type="primary" @click="load">重试</el-button></el-alert>
    <el-skeleton v-else-if="loading" :rows="5" animated />
    <template v-else>
      <article v-for="item in items" :key="item.id" class="connection-item" :data-notification-id="item.id" :class="{ 'is-unread': !item.readAt }"><span class="notice-dot" :class="{ read: !!item.readAt }" aria-hidden="true"></span><div class="item-copy"><strong>{{ item.title }}</strong><p>{{ item.actor?.name ?? '学习伙伴' }}<span v-if="item.groupName"> · {{ item.groupName }}</span></p><small>{{ time(item.createdAt) }} · {{ item.readAt ? '已读' : '未读' }}</small></div><div class="item-actions"><el-button :disabled="!!busy" @click="navigate(item)">查看相关列表</el-button><el-button v-if="!item.readAt" :loading="busy === item.id" :disabled="!!busy" @click="mark(item)">标为已读</el-button><el-tag v-else type="info">已读</el-tag></div></article>
      <EmptyState v-if="!items.length" :title="unreadOnly ? '暂无未读通知' : '暂无站内通知'" description="搭子邀请、小组申请及处理结果将在这里显示。" />
    </template>
    <el-pagination v-if="total > 12" v-model:current-page="page" :page-size="12" :total="total" layout="prev, pager, next" />
    <p class="notice-help">通知由真实业务事件产生。标为已读只改变阅读状态；接受邀请或审核申请请进入对应页面。显示时间为北京时间。</p>
  </section>
</template>
<style scoped>
.notification-panel { padding: 24px; min-width: 0; }
.notification-heading { display: flex; align-items: center; justify-content: space-between; gap: 15px; flex-wrap: wrap; margin-bottom: 20px; }
h2 { font-size: 18px; margin: 0; }
.notification-heading p, .notice-help { font-size: 12px; color: var(--text-muted); line-height: 1.8; }
.notice-tools, .item-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.notice-tools .el-button, .item-actions .el-button { margin-left: 0; }
.connection-item { display: flex; align-items: center; gap: 14px; padding: 18px 10px; border-bottom: 1px solid var(--border-light); }
.is-unread { background: #f8f8ff; }
.notice-dot { flex: 0 0 8px; height: 8px; border-radius: 50%; background: var(--primary); }
.notice-dot.read { background: var(--border-light); }
.item-copy { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.item-copy strong { font-size: 14px; }
.item-copy p { margin: 6px 0; font-size: 13px; color: var(--text-secondary); }
.item-copy small { font-size: 11px; color: var(--text-muted); }
.el-pagination { margin: 18px 0; max-width: 100%; }
@media(max-width:760px) { .notification-panel { padding: 16px; } .connection-item { flex-wrap: wrap; align-items: flex-start; } .item-copy { min-width: calc(100% - 30px); } .item-actions { padding-left: 22px; } }
</style>

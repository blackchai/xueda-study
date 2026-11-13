<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { groupsApi } from '@/services/groups'
import type { Checkin } from '@/types/models'
import type { CheckinGroupShare, GroupSummary } from '@/types/groups'
const open = defineModel<boolean>({ required: true })
const props = defineProps<{ checkin: Checkin | null }>()
const groups = ref<GroupSummary[]>([])
const shares = ref<CheckinGroupShare[]>([])
const drafts = ref<Record<string, boolean>>({})
const page = ref(1), total = ref(0)
const loading = ref(false), busy = ref(''), error = ref('')
let generation = 0
async function load(): Promise<void> {
  if (!open.value || !props.checkin) return
  const run = ++generation
  loading.value = true; error.value = ''; groups.value = []; shares.value = []
  try {
    const [joined, existing] = await Promise.all([groupsApi.list({ mine: true, page: page.value }), groupsApi.shares(props.checkin.id)])
    if (run !== generation) return
    if (page.value > Math.max(1, Math.ceil(joined.total / 12))) { page.value = Math.max(1, Math.ceil(joined.total / 12)); return }
    groups.value = joined.items; total.value = joined.total; shares.value = existing.items
    drafts.value = Object.fromEntries(joined.items.map(g => [g.id, existing.items.find(s => s.groupId === g.id)?.shareContent ?? false]))
  } catch (e) { if (run === generation) error.value = e instanceof Error ? e.message : '加载分享设置失败' }
  finally { if (run === generation) loading.value = false }
}
watch(() => open.value, value => { if (value) { page.value = 1; void load() } else { generation++; groups.value = []; shares.value = [] } })
watch(page, () => void load())
const shared = (id: string): boolean => shares.value.some(s => s.groupId === id)
async function save(id: string, remove = false): Promise<void> {
  if (busy.value || !props.checkin) return
  busy.value = id
  try {
    if (remove) await groupsApi.unshare(props.checkin.id, id)
    else await groupsApi.share(props.checkin.id, id, drafts.value[id] ?? false)
    ElMessage.success(remove ? '已撤回本组分享，个人打卡保留' : '分享设置已保存')
    await load()
  } catch (e) { ElMessage.error(e instanceof Error ? e.message : '分享操作失败') }
  finally { busy.value = '' }
}
</script>
<template>
  <el-dialog v-model="open" title="分享到学习小组" width="600px" destroy-on-close :close-on-click-modal="!busy" :show-close="!busy">
    <p v-if="checkin" class="summary">{{ checkin.date }} · {{ checkin.duration }} 分钟<br />{{ checkin.content }}</p>
    <el-alert type="info" :closable="false" title="仅向选定小组的成员公开" description="分享会公开昵称、学习日期和时长；学习内容默认不公开。只能分享本次入组当地日期起的记录，每人每天每组最多 24 小时。退出或被移除后，分享自动撤回，个人记录保留。" />
    <p v-if="loading" role="status">正在读取小组与分享状态…</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button text @click="load">重试</el-button></el-alert>
    <div v-for="group in groups" :key="group.id" class="share-row" :data-share-group="group.id"><div><strong>{{ group.name }}</strong><el-tag v-if="shared(group.id)" type="success" size="small">已分享</el-tag><el-checkbox v-model="drafts[group.id]" :disabled="!!busy" :aria-label="'公开学习内容到' + group.name">公开学习内容</el-checkbox></div><div><el-button type="primary" :loading="busy === group.id" :disabled="!!busy" @click="save(group.id)">{{ shared(group.id) ? '保存分享设置' : '分享至本组' }}</el-button><el-button v-if="shared(group.id)" :disabled="!!busy" @click="save(group.id, true)">撤回分享</el-button></div></div>
    <p v-if="!loading && !error && !groups.length">你还没有加入小组。<router-link to="/groups" @click="open = false">去发现小组</router-link></p>
    <el-pagination v-if="total > 12" v-model:current-page="page" :total="total" :page-size="12" layout="prev, pager, next" />
    <template #footer><el-button :disabled="!!busy" @click="open = false">完成</el-button></template>
  </el-dialog>
</template>
<style scoped>
.summary { color: var(--text-secondary); line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
.share-row { display: flex; align-items: center; justify-content: space-between; padding: 18px 0; border-bottom: 1px solid var(--border-light); gap: 12px; }
.share-row > div:first-child { display: flex; min-width: 0; align-items: flex-start; gap: 8px; flex-direction: column; }
.share-row strong { overflow-wrap: anywhere; }
.share-row > div:last-child { display: flex; flex-wrap: wrap; gap: 8px; }
.share-row .el-button { margin-left: 0; }
@media(max-width:600px) { .share-row { align-items: flex-start; flex-direction: column; } }
</style>

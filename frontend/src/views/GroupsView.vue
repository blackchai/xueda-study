<script setup lang="ts">
import { Plus, Refresh, Search, UserFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/EmptyState.vue'
import GroupFormFields from '@/components/GroupFormFields.vue'
import PageHeader from '@/components/PageHeader.vue'
import { groupsApi } from '@/services/groups'
import { GOAL_CATEGORIES, type GoalCategory } from '@/types/models'
import type { GroupSummary, GroupWritePayload } from '@/types/groups'

const router = useRouter()
const mine = ref(false)
const category = ref<GoalCategory | ''>('')
const searchText = ref('')
const page = ref(1)
const groups = ref<GroupSummary[]>([])
const total = ref(0)
const joinedTotal = ref(0)
const loading = ref(false)
const error = ref('')
const busy = ref('')
const createOpen = ref(false)
const saving = ref(false)
const blank = (): GroupWritePayload => ({ name: '', category: '编程开发', description: '', maxMembers: 30, requiresApproval: true, tags: [], announcement: '' })
const form = ref(blank())
let generation = 0
async function load(): Promise<void> {
  const run = ++generation
  loading.value = true; error.value = ''
  try {
    const result = await groupsApi.list({ q: searchText.value.trim(), category: category.value || undefined, mine: mine.value, page: page.value })
    if (run !== generation) return
    if (page.value > Math.max(1, Math.ceil(result.total / 12))) { page.value = Math.max(1, Math.ceil(result.total / 12)); return }
    groups.value = result.items; total.value = result.total; joinedTotal.value = result.joinedTotal
  } catch (e) { if (run === generation) { groups.value = []; error.value = e instanceof Error ? e.message : '加载小组失败' } }
  finally { if (run === generation) loading.value = false }
}
function search(): void { if (page.value === 1) void load(); else page.value = 1 }
watch([mine, category], search)
watch(page, () => void load())
onMounted(() => void load())
async function create(): Promise<void> {
  if (saving.value) return
  if (form.value.name.trim().length < 2 || !form.value.description.trim()) { ElMessage.warning('请填写至少两个字的小组名称和小组介绍'); return }
  saving.value = true
  try {
    const group = await groupsApi.create(form.value)
    createOpen.value = false; ElMessage.success('小组已创建，你已成为组长')
    await router.push('/groups/' + group.id)
  } catch (e) { ElMessage.error(e instanceof Error ? e.message : '创建失败') }
  finally { saving.value = false }
}
async function join(group: GroupSummary): Promise<void> {
  if (busy.value) return
  busy.value = group.id
  try {
    const result = await groupsApi.join(group.id)
    ElMessage.success(result.state === 'pending' ? '申请已提交，等待组长审核' : '已加入小组')
    await load()
  } catch (e) { ElMessage.error(e instanceof Error ? e.message : '加入失败') }
  finally { busy.value = '' }
}
</script>
<template>
  <div class="groups-view">
    <PageHeader eyebrow="STUDY GROUP" title="学习小组" description="共同的方向，各自的成长。把每一次投入，汇成一群人的前进。">
      <template #actions><el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button><el-button type="primary" :icon="Plus" @click="form = blank(); createOpen = true">创建小组</el-button></template>
    </PageHeader>
    <section class="group-hero">
      <div><span>共同目标，会让坚持更具体</span><h2>在一群认真学习的人中，<br />找到属于你的节奏。</h2><p>由你选择分享的学习记录，才会出现在小组中。</p></div>
      <div class="hero-people" aria-hidden="true"><span>学</span><span>习</span><span>同</span><span>行</span><i></i><i></i></div>
      <div class="hero-stats"><span><strong>{{ joinedTotal }}</strong>个已加入</span></div>
    </section>
    <form class="groups-toolbar" @submit.prevent="search">
      <div class="group-tabs" aria-label="小组列表筛选"><button type="button" :class="{ active: !mine }" :aria-pressed="!mine" @click="mine = false">发现小组</button><button type="button" :class="{ active: mine }" :aria-pressed="mine" @click="mine = true">我加入的 <span>{{ joinedTotal }}</span></button></div>
      <div class="group-search"><Search /><el-input v-model="searchText" aria-label="搜索小组" placeholder="搜索名称或介绍，回车搜索" clearable @clear="search" /></div>
      <el-select v-model="category" aria-label="按方向筛选小组"><el-option label="全部方向" value="" /><el-option v-for="c in GOAL_CATEGORIES" :key="c" :label="c" :value="c" /></el-select>
    </form>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon><el-button text @click="load">重新加载</el-button></el-alert>
    <p v-if="loading" role="status">正在加载小组…</p>
    <section v-else-if="groups.length" class="group-grid" aria-label="学习小组列表">
      <article v-for="group in groups" :key="group.id" class="group-card surface-card surface-card--interactive" :data-group-id="group.id">
        <div class="group-cover" :class="'cover-' + group.category.length % 4"><span>{{ group.category }}</span><div class="cover-symbol"><UserFilled /></div><small>{{ group.requiresApproval ? '审核加入' : '直接加入' }}</small></div>
        <div class="group-card__body">
          <div class="group-title-row"><h2>{{ group.name }}</h2><el-tag v-if="group.isJoined" type="success" size="small">{{ group.myRole === 'owner' ? '组长' : '已加入' }}</el-tag><el-tag v-else-if="group.joinRequest?.status === 'pending'" size="small">审核中</el-tag></div>
          <p>{{ group.description }}</p>
          <div class="tag-list"><span v-for="tag in group.tags" :key="tag" class="soft-tag">{{ tag }}</span></div>
          <div class="group-progress"><div><span>{{ group.memberCount }}/{{ group.maxMembers }} 人</span><span>组长 · {{ group.ownerName }}</span></div><el-progress :percentage="Math.min(100, Math.round(group.memberCount / group.maxMembers * 100))" :show-text="false" :stroke-width="7" /></div>
          <div class="group-actions"><el-button @click="router.push('/groups/' + group.id)">{{ group.myRole === 'owner' ? '管理小组' : '查看小组' }}</el-button>
            <el-button v-if="!group.isJoined" type="primary" :loading="busy === group.id" :disabled="group.joinRequest?.status === 'pending' || group.memberCount >= group.maxMembers" @click="join(group)">{{ group.joinRequest?.status === 'pending' ? '等待审核' : group.memberCount >= group.maxMembers ? '人数已满' : group.requiresApproval ? '申请加入' : '立即加入' }}</el-button>
            <el-button v-else type="primary" plain @click="router.push('/groups/' + group.id)">进入小组</el-button>
          </div>
        </div>
      </article>
    </section>
    <EmptyState v-else-if="!error" title="还没有找到学习小组" description="换一个方向搜索，或创建属于你的主题小组。" />
    <el-pagination v-if="total > 12" v-model:current-page="page" :total="total" :page-size="12" layout="prev, pager, next" />
    <el-dialog v-model="createOpen" title="创建学习小组" width="600px" destroy-on-close :close-on-click-modal="!saving" :show-close="!saving">
      <GroupFormFields v-model="form" />
      <template #footer><el-button :disabled="saving" @click="createOpen = false">取消</el-button><el-button type="primary" :loading="saving" @click="create">确认创建</el-button></template>
    </el-dialog>
  </div>
</template>
<style scoped>
.group-hero { position: relative; display: grid; min-height: 205px; align-items: center; padding: 30px 36px; margin-bottom: 22px; overflow: hidden; border-radius: 22px; color: #fff; background: linear-gradient(125deg, #4d50c7, #6659d9 65%, #7458cf); box-shadow: 0 20px 45px rgba(76, 72, 181, 0.18); grid-template-columns: 1fr 0.65fr; }
.group-hero > div:first-child { z-index: 2; }
.group-hero > div:first-child > span { color: #cfd0ff; font-size: 9px; font-weight: 800; letter-spacing: 0.12em; }
.group-hero h2 { margin: 8px 0 9px; font-size: clamp(23px, 3vw, 34px); letter-spacing: -0.04em; line-height: 1.35; }
.group-hero p { margin: 0; color: #dedfff; font-size: 10px; }
.hero-people { position: relative; display: flex; height: 110px; align-items: center; justify-content: center; }
.hero-people > span { z-index: 2; display: grid; width: 53px; height: 53px; margin-left: -8px; place-items: center; border: 3px solid rgba(255, 255, 255, 0.82); border-radius: 17px; color: #fff; background: #8982eb; box-shadow: 0 9px 24px rgba(32, 30, 99, 0.22); font-weight: 850; transform: rotate(-5deg); }
.hero-people > span:nth-child(2) { background: #3cb1bb; transform: translateY(-20px) rotate(5deg); }
.hero-people > span:nth-child(3) { background: #e69058; transform: rotate(4deg); }
.hero-people > span:nth-child(4) { background: #8e68d3; transform: translateY(16px) rotate(-4deg); }
.hero-people > span:nth-child(5) { background: rgba(255, 255, 255, 0.15); }
.hero-people i { position: absolute; width: 240px; height: 90px; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 50%; }
.hero-people i:nth-last-child(2) { width: 310px; height: 130px; }
.hero-stats { position: absolute; right: 25px; bottom: 15px; display: flex; color: #d5d6ff; font-size: 8px; gap: 12px; }
.hero-stats strong { margin-right: 3px; color: #fff; font-size: 12px; }
.groups-toolbar { display: grid; align-items: center; margin-bottom: 17px; gap: 10px; grid-template-columns: 1fr 240px 150px; }
.group-tabs { display: flex; align-items: center; gap: 5px; }
.group-tabs button { min-height: 37px; padding: 0 15px; border: 0; border-radius: 9px; color: var(--text-secondary); background: transparent; cursor: pointer; font-size: 11px; font-weight: 750; }
.group-tabs button.active { color: var(--primary); background: var(--primary-soft); }
.group-tabs button span { margin-left: 3px; color: var(--text-muted); font-size: 8px; }
.group-search { position: relative; }
.group-search > svg { position: absolute; z-index: 2; top: 12px; left: 12px; width: 15px; color: var(--text-muted); }
.group-search :deep(.el-input__wrapper) { padding-left: 34px; }
.group-grid { display: grid; gap: 18px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.group-card { overflow: hidden; }
.group-cover { position: relative; display: flex; height: 112px; align-items: flex-start; justify-content: space-between; padding: 17px; overflow: hidden; color: #fff; background: linear-gradient(135deg, #5b5ce2, #8371ed); }
.group-cover::before, .group-cover::after { position: absolute; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 50%; content: ''; }
.group-cover::before { right: -45px; bottom: -80px; width: 180px; height: 180px; }
.group-cover::after { right: 5px; bottom: -55px; width: 120px; height: 120px; }
.cover-1 { background: linear-gradient(135deg, #3e9fab, #48c0b2); }
.cover-2 { background: linear-gradient(135deg, #d47b48, #eda55e); }
.cover-3 { background: linear-gradient(135deg, #8056c6, #a875db); }
.group-cover > span, .group-cover > small { z-index: 1; padding: 5px 8px; border-radius: 999px; background: rgba(255, 255, 255, 0.14); font-size: 8px; font-weight: 750; }
.cover-symbol { position: absolute; z-index: 1; right: 50%; bottom: 14px; transform: translateX(50%); }
.cover-symbol svg { width: 38px; opacity: 0.88; }
.group-card__body { padding: 20px; }
.group-title-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.group-title-row h2 { overflow: hidden; margin: 0; font-size: 16px; text-overflow: ellipsis; white-space: nowrap; }
.group-card__body > p { min-height: 54px; margin: 8px 0 12px; color: var(--text-secondary); font-size: 10px; line-height: 1.75; }
.group-progress { padding: 14px 0; margin-top: 13px; border-top: 1px solid var(--border-light); }
.group-progress > div { display: flex; justify-content: space-between; margin-bottom: 7px; color: var(--text-muted); font-size: 8px; }
.group-progress span { display: inline-flex; align-items: center; gap: 4px; }
.group-progress svg { width: 11px; }
.member-preview { display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px; }
.member-preview > div { display: flex; }
.member-preview > div span, .member-preview > div i { display: grid; width: 27px; height: 27px; margin-right: -7px; place-items: center; border: 2px solid #fff; border-radius: 9px; color: #fff; background: #7675de; font-size: 8px; font-style: normal; font-weight: 800; }
.member-preview > div span:nth-child(2) { background: #3fa7ae; }
.member-preview > div span:nth-child(3) { background: #dc8a54; }
.member-preview > div span:nth-child(4) { background: #9a70d0; }
.member-preview > div i { color: var(--text-muted); background: #eceef4; }
.member-preview small { overflow: hidden; max-width: 140px; color: var(--text-muted); font-size: 7px; text-overflow: ellipsis; white-space: nowrap; }
.group-actions { display: grid; gap: 8px; grid-template-columns: 1fr 1fr; }
.group-form { display: flex; margin-top: 16px; gap: 8px; flex-direction: column; }
.group-form > label, .group-form__row label { display: block; margin-top: 7px; margin-bottom: 5px; color: var(--text-secondary); font-size: 10px; font-weight: 750; }
.group-form :deep(.el-select) { width: 100%; }
.group-form__row { display: grid; gap: 20px; grid-template-columns: 1fr 0.7fr; }
.detail-badge { display: flex; align-items: center; justify-content: space-between; }
.detail-badge > span { color: var(--primary); font-size: 10px; font-weight: 800; }
.detail-description { color: var(--text-secondary); font-size: 11px; line-height: 1.8; }
.announcement { padding: 14px; margin: 18px 0; border: 1px solid #e4e5fb; border-radius: 13px; background: #f7f7ff; }
.announcement strong { color: var(--primary-dark); font-size: 10px; }
.announcement p { margin: 6px 0 0; color: var(--text-secondary); font-size: 9px; line-height: 1.7; }
.detail-metrics { display: grid; padding: 16px 0; margin-bottom: 24px; border-top: 1px solid var(--border-light); border-bottom: 1px solid var(--border-light); grid-template-columns: repeat(3, 1fr); }
.detail-metrics div { display: flex; align-items: center; border-right: 1px solid var(--border-light); flex-direction: column; }
.detail-metrics div:last-child { border: 0; }
.detail-metrics strong { font-size: 17px; }
.detail-metrics small { color: var(--text-muted); font-size: 7px; }
.group-detail .section-title > svg { width: 18px; color: var(--primary); }
.ranking-list article { display: flex; align-items: center; padding: 12px 6px; border-bottom: 1px solid var(--border-light); gap: 9px; }
.ranking-list article.me { border-radius: 10px; background: var(--primary-soft); }
.rank { width: 25px; color: var(--text-muted); font-size: 11px; text-align: center; }
.ranking-list article > div { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.ranking-list article div strong { font-size: 10px; }
.ranking-list article div strong small { padding: 2px 4px; border-radius: 4px; color: var(--primary); background: #fff; font-size: 6px; }
.ranking-list article div span { margin-top: 2px; color: var(--text-muted); font-size: 7px; }
.ranking-list article > b { color: var(--primary); font-size: 11px; }
.group-detail__actions { display: flex; margin-top: 24px; }
.group-detail__actions :deep(.el-button) { flex: 1; }

@media (max-width: 1200px) { .group-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 720px) {
  .group-hero { display: block; min-height: 215px; padding: 25px; }
  .hero-people { position: absolute; right: -30px; bottom: 1px; opacity: 0.45; transform: scale(0.75); }
  .hero-stats { right: auto; left: 25px; }
  .groups-toolbar { grid-template-columns: 1fr 1fr; }
  .group-tabs { grid-column: 1 / -1; }
  .group-search { grid-column: 1 / -1; }
  .group-grid { grid-template-columns: 1fr; }
  .group-form__row { grid-template-columns: 1fr; gap: 0; }
}
</style>

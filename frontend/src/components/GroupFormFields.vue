<script setup lang="ts">
import { GOAL_CATEGORIES } from '@/types/models'
import type { GroupWritePayload } from '@/types/groups'
const model = defineModel<GroupWritePayload>({ required: true })
</script>
<template>
  <div class="group-fields">
    <label>小组名称<el-input v-model="model.name" aria-label="小组名称" maxlength="50" show-word-limit placeholder="例如：C++ 晚间自习室" /></label>
    <label>学习方向<el-select v-model="model.category" aria-label="小组学习方向"><el-option v-for="c in GOAL_CATEGORIES" :key="c" :label="c" :value="c" /></el-select></label>
    <label>小组介绍<el-input v-model="model.description" aria-label="小组介绍" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="适合谁、如何共学、共同约定" /></label>
    <label>标签<el-select v-model="model.tags" aria-label="小组标签" multiple filterable allow-create default-first-option :multiple-limit="10" placeholder="输入后回车，每项不超过 32 字"><el-option v-for="tag in model.tags" :key="tag" :label="tag" :value="tag" /></el-select></label>
    <div class="field-row">
      <label>人数上限<el-input-number v-model="model.maxMembers" aria-label="人数上限" :min="2" :max="200" :precision="0" /></label>
      <label>加入方式<el-switch v-model="model.requiresApproval" aria-label="加入需要审核" active-text="需要组长审核" inactive-text="直接加入" /></label>
    </div>
    <label>成员公告<el-input v-model="model.announcement" aria-label="成员公告" type="textarea" :rows="2" maxlength="500" placeholder="仅加入后的成员可见" /></label>
    <p>小组名称、简介和人数用于公开发现；成员、公告、学习动态和排行榜仅组员可见。</p>
  </div>
</template>
<style scoped>
.group-fields { display: grid; gap: 16px; }
label { display: grid; gap: 7px; color: var(--text-secondary); font-size: 13px; }
.el-select { width: 100%; }
.field-row { display: flex; flex-wrap: wrap; gap: 18px; }
p { margin: 0; color: var(--text-muted); font-size: 12px; line-height: 1.7; }
</style>

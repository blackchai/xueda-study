<script setup lang="ts">
import type { PublicBuddyProfile } from '@/types/matching'

defineProps<{ profile: PublicBuddyProfile; compact?: boolean }>()
const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
</script>

<template>
  <div class="public-study-profile">
    <div v-if="!compact" class="public-person"><span class="avatar">{{ profile.avatar }}</span><strong>{{ profile.name }}</strong></div>
    <el-alert v-if="profile.profileVisible === false" title="对方当前未公开匹配档案，且你们没有待处理邀请或有效搭子关系。" type="info" :closable="false" />
    <template v-else>
      <h3>学习方向和公开目标</h3>
      <p>{{ profile.categories.join('、') || '方向未设置' }}</p>
      <div class="tag-list"><span v-for="tag in profile.tags" :key="tag" class="soft-tag">{{ tag }}</span></div>
      <p>学习方式：{{ profile.styles.join('、') || '未设置' }}</p>
      <p>当前阶段：{{ profile.stage ?? '未设置' }}</p>
      <h3>每周学习计划 · 北京时间 UTC+8</h3>
      <p v-for="(slot, index) in profile.timeSlots" :key="index">{{ days[slot.day - 1] }} {{ slot.start }}–{{ slot.end }}</p>
      <p v-if="!profile.timeSlots.length">尚未设置可用时段</p>
    </template>
    <p class="privacy-note">这里只展示匹配档案，邮箱、学校、专业、个人简介、私人学习任务和打卡记录不会共享。</p>
  </div>
</template>

<style scoped>
.public-person { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
h3 { margin-top: 24px; font-size: 15px; }
p { color: var(--text-secondary); font-size: 13px; line-height: 1.8; }
.privacy-note { padding: 12px; margin-top: 24px; border-radius: 12px; background: var(--surface-muted); font-size: 12px; }
</style>

<script setup lang="ts">
import { Bell } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notifications'
const router = useRouter(), store = useNotificationStore()
</script>
<template><el-badge :value="store.unreadCount" :max="99" :hidden="!store.unreadCount" class="notification-bell"><el-button :icon="Bell" circle aria-label="打开通知中心" :title="store.error || '站内通知'" @click="router.push('/notifications')" /><span v-if="store.error" class="sync-error" aria-label="通知暂时无法同步">!</span></el-badge></template>
<style scoped>.notification-bell { position: relative; flex-shrink: 0; }.sync-error { position: absolute; top: -5px; right: -5px; border-radius: 50%; background: #b95112; color: white; width: 17px; height: 17px; text-align: center; font-size: 12px; }</style>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import GroupDetailPanel from '@/components/GroupDetailPanel.vue'
const route = useRoute(), router = useRouter()
const groupId = computed(() => String(route.params.groupId))
</script>
<template><div><PageHeader eyebrow="LEARN TOGETHER" title="小组共学空间" description="分享你愿意公开的努力，和同伴一起向前。"><template #actions><el-button @click="router.push('/groups')">返回小组</el-button></template></PageHeader><GroupDetailPanel :group-id="groupId" :initial-tab="String(route.query.tab ?? '')" @closed="router.push('/groups')" /></div></template>

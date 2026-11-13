<script setup lang="ts">
withDefaults(defineProps<{ title: string; description: string; symbol?: string }>(), { symbol: '✦' })
</script>

<template>
  <div class="empty-state" role="status">
    <span aria-hidden="true">{{ symbol }}</span>
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  min-height: 230px;
  align-items: center;
  justify-content: center;
  padding: 32px;
  color: var(--text-secondary);
  text-align: center;
  flex-direction: column;
}

.empty-state > span {
  display: grid;
  width: 52px;
  height: 52px;
  margin-bottom: 14px;
  place-items: center;
  border-radius: 18px;
  color: var(--primary);
  background: var(--primary-soft);
  font-size: 22px;
}

.empty-state strong { color: var(--text-strong); font-size: 16px; }
.empty-state p { max-width: 330px; margin: 7px 0 16px; font-size: 13px; line-height: 1.7; }
</style>


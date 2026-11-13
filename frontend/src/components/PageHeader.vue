<script setup lang="ts">
defineProps<{
  eyebrow?: string
  title: string
  description?: string
}>()
</script>

<template>
  <header class="page-heading">
    <div>
      <span v-if="eyebrow" class="page-heading__eyebrow">{{ eyebrow }}</span>
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-heading__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 26px;
}

.page-heading__eyebrow {
  display: block;
  margin-bottom: 7px;
  color: var(--primary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: var(--text-strong);
  font-size: clamp(26px, 3vw, 34px);
  letter-spacing: -0.04em;
}

p {
  max-width: 700px;
  margin: 9px 0 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.page-heading__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  flex: 0 0 auto;
  gap: 10px;
}

@media (max-width: 680px) {
  .page-heading {
    align-items: stretch;
    flex-direction: column;
    gap: 16px;
  }

  .page-heading__actions :deep(.el-button) {
    flex: 1;
  }
}
</style>


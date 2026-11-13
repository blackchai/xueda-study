<script setup lang="ts">
import type { Component } from 'vue'

withDefaults(
  defineProps<{
    label: string
    value: string | number
    suffix?: string
    hint?: string
    icon: Component
    tone?: 'violet' | 'cyan' | 'orange' | 'green'
  }>(),
  { suffix: '', hint: '', tone: 'violet' },
)
</script>

<template>
  <article class="stat-card surface-card">
    <span class="stat-card__icon" :class="`tone-${tone}`" aria-hidden="true">
      <component :is="icon" />
    </span>
    <div class="stat-card__content">
      <span class="stat-card__label">{{ label }}</span>
      <strong>{{ value }}<small v-if="suffix">{{ suffix }}</small></strong>
      <span v-if="hint" class="stat-card__hint">{{ hint }}</span>
    </div>
  </article>
</template>

<style scoped>
.stat-card {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 14px;
  padding: 19px;
}

.stat-card__icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  place-items: center;
  border-radius: 13px;
  font-size: 20px;
}

.tone-violet { color: #5b5ce2; background: #eeefff; }
.tone-cyan { color: #188da0; background: #e4f7fa; }
.tone-orange { color: #d77532; background: #fff0e5; }
.tone-green { color: #168369; background: #e5f7f2; }

.stat-card__content {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.stat-card__label {
  margin-bottom: 4px;
  color: var(--text-muted);
  font-size: 13px;
}

.stat-card strong {
  color: var(--text-strong);
  font-size: 25px;
  letter-spacing: -0.04em;
  line-height: 1.25;
}

.stat-card strong small {
  margin-left: 4px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.stat-card__hint {
  overflow: hidden;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>


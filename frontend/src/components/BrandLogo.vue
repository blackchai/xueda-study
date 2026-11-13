<script setup lang="ts">
withDefaults(
  defineProps<{
    compact?: boolean
    inverted?: boolean
  }>(),
  { compact: false, inverted: false },
)
</script>

<template>
  <RouterLink class="brand-logo" :class="{ 'is-inverted': inverted }" to="/" aria-label="学搭首页">
    <span class="brand-logo__mark" aria-hidden="true">
      <span class="brand-logo__book"></span>
      <span class="brand-logo__spark">✦</span>
    </span>
    <span v-if="!compact" class="brand-logo__copy">
      <strong>学搭</strong>
      <small>StudyMate</small>
    </span>
  </RouterLink>
</template>

<style scoped>
.brand-logo {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  color: var(--text-strong);
  text-decoration: none;
}

.brand-logo__mark {
  position: relative;
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  overflow: hidden;
  border-radius: 13px;
  background: linear-gradient(145deg, #6c68ef, #5149d8);
  box-shadow: 0 8px 22px rgba(91, 92, 226, 0.28);
}

.brand-logo__book {
  position: absolute;
  top: 13px;
  left: 10px;
  width: 21px;
  height: 16px;
  border: 2px solid #fff;
  border-top: 0;
  border-radius: 2px 2px 5px 5px;
}

.brand-logo__book::after {
  position: absolute;
  top: 0;
  left: 9px;
  width: 2px;
  height: 14px;
  content: '';
  background: rgba(255, 255, 255, 0.82);
}

.brand-logo__spark {
  position: absolute;
  top: 4px;
  right: 5px;
  color: #c9f4ff;
  font-size: 11px;
}

.brand-logo__copy {
  display: flex;
  flex-direction: column;
  line-height: 1;
}

.brand-logo__copy strong {
  font-size: 20px;
  letter-spacing: 0.08em;
}

.brand-logo__copy small {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.brand-logo.is-inverted,
.brand-logo.is-inverted .brand-logo__copy small {
  color: #fff;
}
</style>


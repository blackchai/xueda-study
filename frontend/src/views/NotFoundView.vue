<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
</script>

<template>
  <main id="main-content" class="not-found" tabindex="-1">
    <span>404</span>
    <h1>这页学习笔记还没写</h1>
    <p>你访问的页面不存在，返回工作台继续今天的计划吧。</p>
    <RouterLink to="/dashboard"><ArrowLeft /> 返回学习工作台</RouterLink>
  </main>
</template>

<style scoped>
.not-found { display: flex; min-height: 100vh; align-items: center; justify-content: center; padding: 24px; background: radial-gradient(circle at 50% 35%, #eeeefe, #f8f9fc 55%); text-align: center; flex-direction: column; outline: none; }
.not-found > span { color: var(--primary); font-size: clamp(80px, 15vw, 150px); font-weight: 900; letter-spacing: -0.08em; opacity: 0.18; line-height: 1; }
.not-found h1 { margin: -10px 0 8px; color: var(--text-strong); }
.not-found p { margin: 0 0 22px; color: var(--text-secondary); }
.not-found a { display: inline-flex; min-height: 42px; align-items: center; padding: 0 17px; border-radius: 10px; color: #fff; background: var(--primary); font-weight: 700; gap: 7px; text-decoration: none; }
.not-found svg { width: 15px; }
</style>

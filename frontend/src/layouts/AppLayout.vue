<script setup lang="ts">
import {
  Calendar,
  ChatDotRound,
  Clock,
  CollectionTag,
  House,
  Menu as MenuIcon,
  Setting,
  User,
  UserFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BrandLogo from '@/components/BrandLogo.vue'
import NotificationBell from '@/components/NotificationBell.vue'
import { clearAuthenticatedUser, getAuthenticatedUser } from '@/services/authSession'
import { useNotificationStore } from '@/stores/notifications'
import { useProfileStore } from '@/stores/profile'
import { useStudyStore } from '@/stores/study'
import type { AuthenticatedUser } from '@/types/api'

const route = useRoute()
const router = useRouter()
const profileStore = useProfileStore()
const studyStore = useStudyStore()
const notifications = useNotificationStore()
let notificationTimer: number | undefined
function syncNotifications(): void { if (document.visibilityState === 'visible' && navigator.onLine) void notifications.refreshCount() }
watch(() => notifications.expired, expired => {
  if (!expired) return
  clearAuthenticatedUser(); studyStore.clearAccountData(); profileStore.clearAccountData()
  void router.replace({ name: 'auth', query: { redirect: route.fullPath } })
})
const mobileMenuOpen = ref(false)
const compactSidebar = ref(false)
const authenticatedUser = ref<AuthenticatedUser>()

const navItems = [
  { path: '/dashboard', label: '学习工作台', shortLabel: '工作台', icon: House },
  { path: '/goals', label: '目标管理', shortLabel: '目标', icon: CollectionTag },
  { path: '/checkins', label: '学习打卡', shortLabel: '打卡', icon: Calendar },
  { path: '/buddies', label: '学习搭子', shortLabel: '搭子', icon: UserFilled },
  { path: '/groups', label: '学习小组', shortLabel: '小组', icon: ChatDotRound },
  { path: '/profile', label: '个人中心', shortLabel: '我的', icon: User },
]

const pageTitle = computed(() => (typeof route.meta.title === 'string' ? route.meta.title : '学搭'))
const accountName = computed(() => profileStore.initialized ? profileStore.profile.name : authenticatedUser.value?.displayName ?? '同学')
const accountAvatar = computed(() => accountName.value.trim().slice(0, 1) || '学')

function updateViewport(): void {
  compactSidebar.value = window.innerWidth < 1180 && window.innerWidth >= 820
  if (window.innerWidth >= 820) mobileMenuOpen.value = false
}

function navigate(path: string): void {
  mobileMenuOpen.value = false
  void router.push(path)
}

onMounted(() => {
  syncNotifications()
  notificationTimer = window.setInterval(syncNotifications, 60_000)
  document.addEventListener('visibilitychange', syncNotifications)
  window.addEventListener('online', syncNotifications)
  updateViewport()
  window.addEventListener('resize', updateViewport)
  void studyStore.initialize().catch(() => {
    ElMessage.error(studyStore.error || '学习数据加载失败')
  })
  void profileStore.initialize().catch(() => {
    ElMessage.error(profileStore.error || '学习档案加载失败')
  })
  void getAuthenticatedUser().then((user) => {
    authenticatedUser.value = user
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateViewport)
  window.clearInterval(notificationTimer)
  document.removeEventListener('visibilitychange', syncNotifications)
  window.removeEventListener('online', syncNotifications)
  notifications.reset()
})
</script>

<template>
  <div class="app-shell" :class="{ 'is-compact': compactSidebar }">
    <aside class="app-sidebar" aria-label="主要导航">
      <BrandLogo :compact="compactSidebar" />
      <nav class="app-sidebar__nav">
        <button
          v-for="item in navItems"
          :key="item.path"
          type="button"
          class="nav-item"
          :class="{ 'is-active': (route.path === item.path || (item.path === '/groups' && route.path.startsWith('/groups/'))) }"
          :aria-current="(route.path === item.path || (item.path === '/groups' && route.path.startsWith('/groups/'))) ? 'page' : undefined"
          :title="compactSidebar ? item.label : undefined"
          @click="navigate(item.path)"
        >
          <component :is="item.icon" aria-hidden="true" />
          <span v-if="!compactSidebar">{{ item.label }}</span>
        </button>
      </nav>

      <div v-if="!compactSidebar" class="sidebar-focus-card">
        <span class="sidebar-focus-card__icon"><Clock /></span>
        <strong>今日专注</strong>
        <p>完成 {{ studyStore.todayTasks.filter((task) => task.completed).length }}/{{ studyStore.todayTasks.length }} 项任务</p>
        <el-progress
          :percentage="studyStore.todayTasks.length ? Math.round(studyStore.todayTasks.filter((task) => task.completed).length / studyStore.todayTasks.length * 100) : 0"
          :show-text="false"
          :stroke-width="7"
        />
      </div>

      <button class="sidebar-profile" type="button" @click="navigate('/profile')">
        <span class="avatar avatar--small">{{ accountAvatar }}</span>
        <span v-if="!compactSidebar">
          <strong>{{ accountName }}</strong>
          <small>查看个人档案</small>
        </span>
        <Setting v-if="!compactSidebar" aria-hidden="true" />
      </button>
    </aside>

    <header class="mobile-header">
      <button class="icon-button" type="button" aria-label="打开导航菜单" @click="mobileMenuOpen = true">
        <MenuIcon />
      </button>
      <BrandLogo />
      <NotificationBell />
      <button class="avatar avatar--small" type="button" aria-label="进入个人中心" @click="navigate('/profile')">
        {{ accountAvatar }}
      </button>
    </header>

    <main id="main-content" v-loading="studyStore.loading" element-loading-text="正在加载你的学习数据" class="app-main" tabindex="-1">
      <div class="app-main__topline">
        <span>{{ pageTitle }}</span>
        <span>连续学习 {{ studyStore.streakDays }} 天 · 今天也在稳步向前</span>
        <NotificationBell />
      </div>
      <el-alert v-if="studyStore.error" class="data-error" type="error" :title="studyStore.error" show-icon :closable="false">
        <template #default><el-button link type="primary" @click="studyStore.initialize(true)">重试</el-button></template>
      </el-alert>
      <RouterView />
    </main>

    <nav class="mobile-bottom-nav" aria-label="移动端主要导航">
      <button
        v-for="item in navItems"
        :key="item.path"
        type="button"
        :class="{ 'is-active': (route.path === item.path || (item.path === '/groups' && route.path.startsWith('/groups/'))) }"
        :aria-label="item.label"
        :aria-current="(route.path === item.path || (item.path === '/groups' && route.path.startsWith('/groups/'))) ? 'page' : undefined"
        @click="navigate(item.path)"
      >
        <component :is="item.icon" />
        <span>{{ item.shortLabel }}</span>
      </button>
    </nav>

    <el-drawer v-model="mobileMenuOpen" direction="ltr" size="min(84vw, 320px)" :show-close="false">
      <template #header>
        <BrandLogo />
      </template>
      <nav class="drawer-nav" aria-label="移动端完整导航">
        <button
          v-for="item in navItems"
          :key="item.path"
          type="button"
          :class="{ 'is-active': (route.path === item.path || (item.path === '/groups' && route.path.startsWith('/groups/'))) }"
          @click="navigate(item.path)"
        >
          <component :is="item.icon" />
          <span>{{ item.label }}</span>
        </button>
      </nav>
      <div class="prototype-note">
        <strong>{{ studyStore.apiMode ? '真实账号数据' : '开发演示模式' }}</strong>
        <p>{{ studyStore.apiMode ? '目标和打卡由服务端按当前账号隔离保存。' : '当前使用本浏览器 Mock 数据。' }}</p>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding-left: 254px;
  background: var(--app-bg);
  transition: padding-left 0.25s ease;
}

.app-shell.is-compact { padding-left: 88px; }

.app-sidebar {
  position: fixed;
  z-index: 30;
  top: 0;
  bottom: 0;
  left: 0;
  display: flex;
  width: 254px;
  padding: 27px 20px 20px;
  border-right: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(18px);
  flex-direction: column;
  transition: width 0.25s ease;
}

.is-compact .app-sidebar { width: 88px; align-items: center; padding-inline: 14px; }

.app-sidebar__nav {
  display: flex;
  margin-top: 38px;
  gap: 7px;
  flex-direction: column;
}

.nav-item,
.drawer-nav button {
  display: flex;
  width: 100%;
  align-items: center;
  padding: 12px 14px;
  border: 0;
  border-radius: 12px;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  font-weight: 650;
  gap: 12px;
  text-align: left;
  transition: 0.2s ease;
}

.nav-item svg,
.drawer-nav svg { width: 19px; height: 19px; flex: 0 0 auto; }
.nav-item:hover { color: var(--primary); background: var(--primary-soft); transform: translateX(2px); }
.nav-item.is-active { color: #fff; background: linear-gradient(135deg, var(--primary), #7368ed); box-shadow: 0 9px 22px rgba(91, 92, 226, 0.22); }
.is-compact .nav-item { justify-content: center; width: 48px; height: 48px; padding: 0; }

.sidebar-focus-card {
  padding: 17px;
  margin-top: auto;
  border: 1px solid #e5e5ff;
  border-radius: 16px;
  background: linear-gradient(145deg, #f7f7ff, #f0f4ff);
}

.sidebar-focus-card__icon {
  display: grid;
  width: 32px;
  height: 32px;
  margin-bottom: 10px;
  place-items: center;
  border-radius: 10px;
  color: var(--primary);
  background: #fff;
}
.sidebar-focus-card__icon svg { width: 16px; }
.sidebar-focus-card strong { color: var(--text-strong); font-size: 13px; }
.sidebar-focus-card p { margin: 4px 0 11px; color: var(--text-secondary); font-size: 11px; }

.sidebar-profile {
  display: flex;
  width: 100%;
  align-items: center;
  padding: 13px 8px 4px;
  margin-top: 16px;
  border: 0;
  border-top: 1px solid var(--border-light);
  color: var(--text-strong);
  background: transparent;
  cursor: pointer;
  gap: 10px;
  text-align: left;
}
.sidebar-profile > span:nth-child(2) { display: flex; min-width: 0; flex: 1; flex-direction: column; }
.sidebar-profile strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.sidebar-profile small { margin-top: 2px; color: var(--text-muted); font-size: 10px; }
.sidebar-profile svg { width: 15px; color: var(--text-muted); }
.is-compact .sidebar-profile { justify-content: center; padding-inline: 0; }

.app-main {
  width: min(100%, 1500px);
  min-height: 100vh;
  padding: 25px clamp(24px, 4vw, 58px) 56px;
  margin: 0 auto;
  outline: none;
}

.app-main__topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 23px;
  margin-bottom: 27px;
  border-bottom: 1px solid var(--border-light);
  color: var(--text-muted);
  font-size: 12px;
}

.app-main__topline span:first-child { color: var(--text-secondary); font-weight: 750; }
.mobile-header, .mobile-bottom-nav { display: none; }

.drawer-nav { display: flex; flex-direction: column; gap: 8px; }
.drawer-nav button.is-active { color: var(--primary); background: var(--primary-soft); }
.prototype-note { padding: 16px; margin-top: 28px; border-radius: 14px; color: var(--text-secondary); background: var(--surface-muted); }
.prototype-note strong { color: var(--text-strong); font-size: 13px; }
.prototype-note p { margin: 5px 0 0; font-size: 11px; line-height: 1.6; }

@media (max-width: 819px) {
  .app-shell, .app-shell.is-compact { padding: 64px 0 74px; }
  .app-sidebar { display: none; }
  .mobile-header {
    position: fixed;
    z-index: 30;
    top: 0;
    right: 0;
    left: 0;
    display: flex;
    height: 64px;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    border-bottom: 1px solid var(--border-light);
    background: rgba(255, 255, 255, 0.94);
    backdrop-filter: blur(16px);
  }
  .app-main { min-height: auto; padding: 24px 16px 35px; }
  .app-main__topline { display: none; }
  .mobile-bottom-nav {
    position: fixed;
    z-index: 30;
    right: 10px;
    bottom: max(10px, env(safe-area-inset-bottom));
    left: 10px;
    display: grid;
    height: 62px;
    padding: 7px 5px;
    border: 1px solid rgba(224, 226, 239, 0.86);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 12px 35px rgba(38, 42, 72, 0.13);
    backdrop-filter: blur(18px);
    grid-template-columns: repeat(6, 1fr);
  }
  .mobile-bottom-nav button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: 0;
    border-radius: 11px;
    color: var(--text-muted);
    background: transparent;
    font-size: 9px;
    gap: 2px;
    flex-direction: column;
  }
  .mobile-bottom-nav button svg { width: 18px; height: 18px; }
  .mobile-bottom-nav button.is-active { color: var(--primary); background: var(--primary-soft); font-weight: 800; }
}
</style>

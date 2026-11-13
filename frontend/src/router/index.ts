import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { getAuthenticatedUser } from '@/services/authSession'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '首页' },
  },
  {
    path: '/auth',
    name: 'auth',
    component: () => import('@/views/AuthView.vue'),
    meta: { title: '登录与注册' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '学习工作台', navLabel: '工作台' },
      },
      {
        path: 'goals',
        name: 'goals',
        component: () => import('@/views/GoalsView.vue'),
        meta: { title: '目标管理', navLabel: '目标' },
      },
      {
        path: 'checkins',
        name: 'checkins',
        component: () => import('@/views/CheckinsView.vue'),
        meta: { title: '学习打卡', navLabel: '打卡' },
      },
      {
        path: 'buddies',
        name: 'buddies',
        component: () => import('@/views/BuddiesView.vue'),
        meta: { title: '学习搭子', navLabel: '搭子' },
      },
      {
        path: 'groups',
        name: 'groups',
        component: () => import('@/views/GroupsView.vue'),
        meta: { title: '学习小组', navLabel: '小组' },
      },
      {
        path: 'groups/:groupId',
        name: 'group-detail',
        component: () => import('@/views/GroupDetailView.vue'),
        meta: { title: '小组共学空间', navLabel: '小组' },
      },
      {
        path: 'notifications',
        name: 'notifications',
        component: () => import('@/views/NotificationsView.vue'),
        meta: { title: '通知中心' },
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('@/views/ProfileView.vue'),
        meta: { title: '个人中心', navLabel: '我的' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面未找到' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  if (!to.matched.some((record) => record.meta.requiresAuth)) return true
  try {
    await getAuthenticatedUser()
    return true
  } catch {
    return {
      name: 'auth',
      query: { redirect: to.fullPath },
    }
  }
})

router.afterEach((to) => {
  const pageTitle = typeof to.meta.title === 'string' ? to.meta.title : '学习平台'
  document.title = `${pageTitle} · 学搭 StudyMate`
})

export default router

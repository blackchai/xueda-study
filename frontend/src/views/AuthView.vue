<script setup lang="ts">
import { ArrowLeft, Check, Lock, Message, User } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BrandLogo from '@/components/BrandLogo.vue'
import { studyMateApi } from '@/services/api'
import { setAuthenticatedUser } from '@/services/authSession'
import { ApiError } from '@/services/httpClient'
import { useProfileStore } from '@/stores/profile'
import { useStudyStore } from '@/stores/study'

type AuthMode = 'login' | 'register'

const route = useRoute()
const router = useRouter()
const mode = ref<AuthMode>(route.query.mode === 'register' ? 'register' : 'login')
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  username: '',
  email: '',
  account: '',
  password: '',
  confirmPassword: '',
  agreement: false,
})

const title = computed(() => (mode.value === 'login' ? '账号密码登录' : '创建学搭账号'))
const subtitle = computed(() => (mode.value === 'login'
  ? '继续今天的计划，别让已经建立的节奏停下来。'
  : '使用用户名、邮箱和密码创建你的独立学习账号。'))

function validatePassword(_rule: unknown, value: string, callback: (error?: Error) => void): void {
  if (!value) callback(new Error('请输入密码'))
  else if (value.length < 8) callback(new Error('密码至少 8 位'))
  else if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) callback(new Error('密码需同时包含字母和数字'))
  else callback()
}

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z][a-zA-Z0-9_]{2,31}$/, message: '用户名需以字母开头，且为 3–32 位字母、数字或下划线', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  account: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' },
    { min: 3, message: '账号至少 3 个字符', trigger: 'blur' },
  ],
  password: [{ validator: validatePassword, trigger: ['blur', 'change'] }],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== form.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: ['blur', 'change'],
    },
  ],
  agreement: [{
    validator: (_rule, value: boolean, callback) => {
      if (mode.value === 'register' && !value) callback(new Error('请先同意用户协议与隐私说明'))
      else callback()
    },
    trigger: 'change',
  }],
}

function switchMode(next: AuthMode): void {
  mode.value = next
  formRef.value?.clearValidate()
  void router.replace({ query: next === 'register' ? { mode: 'register' } : {} })
}

function safeRedirect(): string {
  return typeof route.query.redirect === 'string'
    && route.query.redirect.startsWith('/')
    && !route.query.redirect.startsWith('//')
    ? route.query.redirect
    : '/dashboard'
}

async function submit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    if (mode.value === 'register') {
      await studyMateApi.register({
        username: form.username,
        email: form.email,
        password: form.password,
        confirmPassword: form.confirmPassword,
      })
      form.account = form.email
      form.password = ''
      form.confirmPassword = ''
      mode.value = 'login'
      await router.replace({})
      ElMessage.success('注册成功，请使用新账号登录')
      return
    }

    const result = await studyMateApi.login({ account: form.account, password: form.password })
    useProfileStore().clearAccountData()
    useStudyStore().clearAccountData()
    setAuthenticatedUser(result.data)
    ElMessage.success('登录成功')
    await router.push(safeRedirect())
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '操作失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <section class="auth-story" aria-label="产品介绍">
      <RouterLink class="back-link" to="/"><ArrowLeft /> 返回首页</RouterLink>
      <BrandLogo inverted />
      <div class="auth-story__content">
        <span class="story-kicker">Study together, grow together</span>
        <h1>一份计划很容易开始，<br />一段同行更容易坚持。</h1>
        <p>设定目标、记录专注、匹配同频搭子。在学搭，每一天的认真都有人看见。</p>
        <ul>
          <li><span><Check /></span><div><strong>安全账号登录</strong><small>Argon2id 密码保护与 HttpOnly 会话</small></div></li>
          <li><span><Check /></span><div><strong>节奏清晰可见</strong><small>用打卡日历看见每一次积累</small></div></li>
          <li><span><Check /></span><div><strong>同行有据</strong><small>四维算法解释每一次搭子推荐</small></div></li>
        </ul>
      </div>
      <div class="quote-card"><span>“</span><p>真正有效的陪伴，不是彼此催促，而是让计划、投入和反馈都清晰可见。</p></div>
      <div class="story-orb story-orb--one"></div>
      <div class="story-orb story-orb--two"></div>
    </section>

    <main id="main-content" class="auth-main" tabindex="-1">
      <div class="auth-card">
        <div class="mobile-brand"><BrandLogo /></div>
        <h2>{{ title }}</h2>
        <p class="auth-subtitle">{{ subtitle }}</p>

        <div class="account-mode-tabs" role="tablist" aria-label="账号操作">
          <button type="button" :class="{ active: mode === 'login' }" role="tab" :aria-selected="mode === 'login'" @click="switchMode('login')">登录</button>
          <button type="button" :class="{ active: mode === 'register' }" role="tab" :aria-selected="mode === 'register'" @click="switchMode('register')">注册</button>
        </div>
        <div class="prototype-alert"><span>安全提示</span>密码只会通过 API 发送给服务端并哈希保存；浏览器不会将密码或会话凭证写入 LocalStorage。</div>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @submit.prevent="submit">
          <template v-if="mode === 'register'">
            <el-form-item label="用户名" prop="username">
              <el-input v-model.trim="form.username" placeholder="以字母开头，3–32 位" autocomplete="username"><template #prefix><User /></template></el-input>
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model.trim="form.email" type="email" placeholder="name@example.com" autocomplete="email"><template #prefix><Message /></template></el-input>
            </el-form-item>
          </template>
          <el-form-item v-else label="用户名或邮箱" prop="account">
            <el-input v-model.trim="form.account" placeholder="输入用户名或邮箱" autocomplete="username"><template #prefix><User /></template></el-input>
          </el-form-item>
            <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位，包含字母和数字" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" @keyup.enter="mode === 'login' && submit()"><template #prefix><Lock /></template></el-input>
            </el-form-item>
          <el-form-item v-if="mode === 'register'" label="确认密码" prop="confirmPassword">
            <el-input v-model="form.confirmPassword" type="password" show-password placeholder="再次输入密码" autocomplete="new-password" @keyup.enter="submit"><template #prefix><Lock /></template></el-input>
          </el-form-item>
            <div v-if="mode === 'login'" class="form-meta">
            <span>会话将按服务端有效期保持</span>
            <button type="button" @click="ElMessage.info('密码找回功能将在下一阶段接入')">忘记密码？</button>
            </div>
          <el-form-item v-else prop="agreement"><el-checkbox v-model="form.agreement">我已阅读并同意用户协议与隐私说明</el-checkbox></el-form-item>
          <el-button class="submit-button" type="primary" native-type="submit" :loading="loading">{{ mode === 'login' ? '登录并进入工作台' : '注册账号' }}</el-button>
        </el-form>
        <p class="switch-copy">
          {{ mode === 'login' ? '第一次来到学搭？' : '已经有账号？' }}
          <button type="button" @click="switchMode(mode === 'login' ? 'register' : 'login')">{{ mode === 'login' ? '立即注册' : '返回登录' }}</button>
        </p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.auth-page { display: grid; min-height: 100vh; background: #f8f9fd; grid-template-columns: minmax(440px, 0.92fr) minmax(560px, 1.08fr); }
.auth-story { position: relative; display: flex; overflow: hidden; padding: 38px clamp(38px, 5vw, 78px); color: #fff; background: linear-gradient(145deg, #4b4cc1 0%, #6655d8 56%, #7a5ad2 100%); flex-direction: column; }
.auth-story :deep(.brand-logo) { position: relative; z-index: 2; margin-top: 45px; }
.back-link { position: relative; z-index: 2; display: inline-flex; align-items: center; align-self: flex-start; color: #dedfff; font-size: 12px; gap: 6px; text-decoration: none; }
.back-link svg { width: 15px; }
.auth-story__content { position: relative; z-index: 2; max-width: 560px; margin: auto 0; }
.story-kicker { color: #c9caff; font-size: 10px; font-weight: 800; letter-spacing: 0.18em; text-transform: uppercase; }
.auth-story h1 { margin: 18px 0 20px; font-size: clamp(36px, 4vw, 55px); letter-spacing: -0.055em; line-height: 1.25; }
.auth-story__content > p { max-width: 500px; margin: 0; color: #dedfff; line-height: 1.9; }
.auth-story ul { display: grid; padding: 0; margin: 33px 0 0; gap: 17px; list-style: none; }
.auth-story li { display: flex; align-items: center; gap: 13px; }
.auth-story li > span { display: grid; width: 31px; height: 31px; flex: 0 0 auto; place-items: center; border-radius: 10px; color: #fff; background: rgba(255, 255, 255, 0.14); }
.auth-story li svg { width: 15px; }
.auth-story li div { display: flex; flex-direction: column; }
.auth-story li strong { font-size: 13px; }
.auth-story li small { margin-top: 2px; color: #ced0f6; font-size: 10px; }
.quote-card { position: relative; z-index: 2; display: flex; max-width: 530px; align-items: flex-start; padding: 14px 17px; border: 1px solid rgba(255, 255, 255, 0.13); border-radius: 14px; color: #e5e5ff; background: rgba(255, 255, 255, 0.08); backdrop-filter: blur(12px); gap: 9px; }
.quote-card > span { color: #bfc0ff; font-size: 25px; line-height: 1; }
.quote-card p { margin: 0; font-size: 11px; line-height: 1.7; }
.story-orb { position: absolute; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 50%; }
.story-orb--one { top: -140px; right: -150px; width: 440px; height: 440px; }
.story-orb--two { right: 40px; bottom: -190px; width: 390px; height: 390px; background: rgba(255, 255, 255, 0.025); }
.auth-main { display: grid; min-width: 0; padding: 42px 24px; place-items: center; outline: none; }
.auth-card { width: min(100%, 465px); box-sizing: border-box; padding: 32px 38px; border: 1px solid #e9eaf2; border-radius: 22px; background: #fff; box-shadow: 0 24px 70px rgba(42, 44, 77, 0.08); }
.mobile-brand { display: none; }
.auth-method-tabs { display: grid; padding: 4px; margin-bottom: 25px; border-radius: 12px; background: #f1f2f7; grid-template-columns: 1fr 1fr; }
.auth-method-tabs button { display: inline-flex; min-height: 38px; align-items: center; justify-content: center; padding: 8px 10px; border: 0; border-radius: 9px; color: var(--text-muted); background: transparent; cursor: pointer; font-size: 12px; font-weight: 750; gap: 7px; }
.auth-method-tabs button.active { color: #292d3d; background: #fff; box-shadow: 0 4px 12px rgba(45, 47, 77, 0.08); }
.account-mode-tabs { display: inline-flex; padding: 3px; margin: -5px 0 18px; border-radius: 9px; background: #f5f5fa; }
.account-mode-tabs button { min-width: 64px; padding: 6px 12px; border: 0; border-radius: 7px; color: #8a8d9d; background: transparent; cursor: pointer; font-size: 11px; font-weight: 700; }
.account-mode-tabs button.active { color: var(--primary); background: #fff; }
.auth-card h2 { margin: 0; color: #292a3e; font-size: 29px; letter-spacing: -0.04em; }
.auth-subtitle { margin: 8px 0 20px; color: var(--text-secondary); font-size: 12px; line-height: 1.65; }
.prototype-alert { padding: 10px 12px; margin-bottom: 19px; border: 1px solid #e3e4fb; border-radius: 10px; color: #666a83; background: #f6f6ff; font-size: 10px; line-height: 1.6; }
.prototype-alert span { margin-right: 5px; color: var(--primary-dark); font-weight: 850; }
.form-meta { display: flex; align-items: center; justify-content: space-between; margin: -5px 0 18px; }
.form-meta button, .switch-copy button { padding: 0; border: 0; color: var(--primary); background: transparent; cursor: pointer; font-size: 12px; font-weight: 700; }
.submit-button, .demo-button { width: 100%; min-height: 44px; }
.divider { display: flex; align-items: center; margin: 19px 0; color: var(--text-muted); font-size: 10px; gap: 10px; }
.divider::before, .divider::after { height: 1px; content: ''; background: #ececf2; flex: 1; }
.switch-copy { margin: 18px 0 0; color: var(--text-muted); font-size: 11px; text-align: center; }

@media (max-width: 900px) {
  .auth-page { display: block; }
  .auth-story { display: none; }
  .auth-main { min-height: 100vh; padding: 30px 16px; }
  .mobile-brand { display: block; margin-bottom: 28px; }
}
@media (max-width: 520px) {
  .auth-main { background: #fff; }
  .auth-card { padding: 22px 6px; border: 0; box-shadow: none; }
}
</style>

import { defineConfig } from '@playwright/test'

const baseURL = process.env.STUDYMATE_E2E_BASE_URL ?? 'http://127.0.0.1:5173'
if (!['127.0.0.1', 'localhost'].includes(new URL(baseURL).hostname)) {
  throw new Error('E2E tests create accounts and must run against an isolated local development server')
}

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  timeout: 90_000,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL,
    headless: true,
    actionTimeout: 10_000,
    viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.STUDYMATE_CHROMIUM_PATH ? { executablePath: process.env.STUDYMATE_CHROMIUM_PATH } : {},
    screenshot: 'only-on-failure',
  },
})

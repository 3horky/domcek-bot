import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e-fullstack',
  globalTeardown: './e2e-fullstack/global-teardown.ts',
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:4175',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } },
    },
    {
      name: 'mobile-chromium',
      use: { ...devices['Pixel 7'] },
    },
  ],
  webServer: [
    {
      command: '../scripts/run_browser_e2e_api.sh',
      url: 'http://127.0.0.1:4180/health/live',
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command:
        'CARLO_E2E_API_TARGET=http://127.0.0.1:4180 npm run dev -- --host 127.0.0.1 --port 4175',
      url: 'http://127.0.0.1:4175',
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
})

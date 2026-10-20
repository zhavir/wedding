import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser', fullyParallel: false, workers: 1,
  use: { baseURL: process.env.WEB_URL || 'http://localhost:5173', trace: 'retain-on-failure', launchOptions: { args: process.env.DOCKER_BROWSER ? ['--host-resolver-rules=MAP localhost floci'] : [] } },
  projects: [ { name: 'desktop', use: { ...devices['Desktop Chrome'] } }, { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } } ]
});

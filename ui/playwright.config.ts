import {defineConfig, devices} from '@playwright/test';

// End-to-end and accessibility tests against the real server and the built UI (npm run build -w ui first).
export default defineConfig({
  testDir: 'tests/e2e',
  testMatch: '**/*.e2e.ts', // not *.test.ts, so vitest leaves them alone
  fullyParallel: false,
  reporter: [['list']],
  use: {baseURL: 'http://127.0.0.1:8799', ...devices['Desktop Chrome']},
  webServer: {
    command: 'uv run python ui/tests/e2e/serve.py 8799',
    cwd: '..',
    url: 'http://127.0.0.1:8799/api/health?token=e2e-token',
    reuseExistingServer: false,
    timeout: 60_000,
  },
});

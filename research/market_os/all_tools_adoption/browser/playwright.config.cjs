const os = require('os');
const path = require('path');

module.exports = {
  testDir: __dirname,
  testMatch: /pilot\.spec\.cjs/,
  timeout: 45000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['line']],
  outputDir: process.env.SHARED_SHELL_TEST_RESULTS_DIR
    || path.join(os.tmpdir(), 'shared-shell-playwright-results'),
  use: {
    baseURL: process.env.SHARED_SHELL_BASE_URL || 'http://127.0.0.1:8877',
    channel: process.env.SHARED_SHELL_BROWSER_CHANNEL || 'chrome',
    headless: true,
    viewport: { width: 1440, height: 1000 },
    ignoreHTTPSErrors: true,
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },
};

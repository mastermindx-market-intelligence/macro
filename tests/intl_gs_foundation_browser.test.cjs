'use strict';
// INTL-GS-W2F browser proof (mission 4.6): the real intl.html via the
// render_fixture seam + the fixture-site stub coverage view, in Chromium.
// Mirrors tests/intl_workspace_page.test.cjs (same route/fixture idiom).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');

function fixtureHtml(stub) {
  const args = [path.join(__dirname, 'intl_gs_fixture_site.py'), '--print-html'];
  if (stub) args.push('--stub-coverage');
  return execFileSync(process.env.INTL_TEST_PYTHON || 'python3', args,
    {cwd: root, env: {...process.env, PYTHONPATH: root}, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024});
}

async function withPage(fn, {query = '', stub = true} = {}) {
  const browser = await chromium.launch({headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  try {
    const html = fixtureHtml(stub);
    const context = await browser.newContext({viewport: {width: 1440, height: 900}});
    const page = await context.newPage();
    page.setDefaultTimeout(6000);
    page.setDefaultNavigationTimeout(30000);
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname !== 'intl.test') return route.abort();
      if (url.pathname === '/intl.html') return route.fulfill({contentType: 'text/html', body: html});
      let file = path.resolve(root, 'templates', '.' + url.pathname);
      if (!file.startsWith(path.join(root, 'templates') + path.sep)) return route.abort();
      if (!fs.existsSync(file)) return route.abort();
      const types = {'.css': 'text/css', '.js': 'text/javascript'};
      return route.fulfill({contentType: types[path.extname(file)] || 'application/octet-stream',
        body: fs.readFileSync(file)});
    });
    await page.goto('https://intl.test/intl.html' + query);
    await fn(page);
  } finally {
    await browser.close();
  }
}

test('production page shows seven disabled surveillance tabs', async () => {
  await withPage(async page => {
    const states = await page.evaluate(() => Object.fromEntries(
      Array.from(document.querySelectorAll('.intl-workspace__view-nav button[data-im-action="set_view"]'))
        .map(button => [button.getAttribute('data-im-view'), button.disabled])));
    for (const view of ['scanner', 'dislocations', 'transmission', 'dossier', 'scenario', 'replay', 'coverage']) {
      assert.ok(view in states, `missing tab ${view}`);
      assert.equal(states[view], true, `${view} must be disabled without a builder`);
    }
    for (const view of ['overview']) assert.equal(states[view], false, `${view} must stay enabled`);
  }, {stub: false});
});

test('coverage tab is enabled, clickable, shows its panel and empties issues', async () => {
  await withPage(async page => {
    const issues = page.locator('[data-im-issues]');
    const unavailable = page.locator('[data-im-unavailable]');
    await issues.textContent().then(text => assert.equal(text, '', 'issues must start empty'));
    const coverage = page.locator('.intl-workspace__view-nav button[data-im-view="coverage"]');
    assert.equal(await coverage.isDisabled(), false, 'coverage must be enabled under the stub');
    await coverage.click();
    await page.waitForTimeout(120);
    const panel = page.locator('[data-im-panel][data-view="coverage"]');
    await panel.waitFor({state: 'visible'});
    assert.equal(await panel.getAttribute('data-im-panel') !== null, true);
    const hiddenOthers = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-im-panel]:not([data-view="coverage"])'))
        .every(node => node.hidden));
    assert.equal(hiddenOthers, true, 'legacy panels must be hidden while coverage shows');
    assert.equal(await issues.textContent(), '', 'issues stays empty after switching');
    assert.equal(await unavailable.isHidden(), true, 'unavailable banner must stay hidden');
    const gsWrapper = await panel.evaluate(node => Boolean(node.closest('.intl-gs')));
    assert.equal(gsWrapper, true, 'coverage panel must render inside the .intl-gs wrapper');
  });
});

test('?view=scanner without a panel behaves like an unsupported view', async () => {
  await withPage(async page => {
    const issues = await page.locator('[data-im-issues]');
    await issues.waitFor({state: 'visible'});
    const text = await issues.textContent();
    assert.equal(text, 'This view is not available yet');
    assert.equal(await page.locator('[data-im-unavailable]').isVisible(), true,
      'unavailable banner must show, exactly like a legacy view with no panel');
    const visible = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-im-panel]')).filter(node => !node.hidden).length);
    assert.equal(visible, 0, 'no panel may be shown for an unbuilt view');
    const scanner = page.locator('.intl-workspace__view-nav button[data-im-view="scanner"]');
    assert.equal(await scanner.isDisabled(), true, 'scanner button stays disabled');
  }, {query: '?view=scanner'});
});

test('legacy views still switch while the surveillance seam exists', async () => {
  await withPage(async page => {
    const overview = page.locator('.intl-workspace__view-nav button[data-im-view="overview"]');
    const coverage = page.locator('.intl-workspace__view-nav button[data-im-view="coverage"]');
    const legacyStates = await page.evaluate(() => Object.fromEntries(
      Array.from(document.querySelectorAll('.intl-workspace__view-nav button[data-im-action="set_view"]'))
        .filter(button => ['overview', 'compare', 'macro', 'risk', 'history', 'library']
          .includes(button.getAttribute('data-im-view')))
        .map(button => [button.getAttribute('data-im-view'), button.disabled])));
    assert.deepEqual(Object.keys(legacyStates),
      ['overview', 'compare', 'macro', 'risk', 'history', 'library']);
    for (let round = 0; round < 2; round++) {
      await coverage.click();
      await page.locator('[data-im-panel][data-view="coverage"]').waitFor({state: 'visible'});
      await overview.click();
      await page.waitForTimeout(120);
      assert.equal(await page.evaluate(() =>
        Array.from(document.querySelectorAll('[data-im-panel][data-view="overview"]'))
          .some(node => !node.hidden)), true, 'overview must come back after coverage');
      assert.equal(await page.evaluate(() =>
        Array.from(document.querySelectorAll('[data-im-panel][data-view="coverage"]'))
          .every(node => node.hidden)), true, 'coverage must hide again');
    }
  });
});

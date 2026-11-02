'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');

const ROOT = path.resolve(__dirname, "..");
const HOME = process.env.HOME || '/home/ubuntu2';
const fixtureEnv = {
  ...process.env,
  PYTHONPATH: '.:/usr/lib/python3/dist-packages',
  PATH: `${HOME}/lanes/artifacts/paper-waves-01a1101f/python-env/bin:${process.env.PATH || ''}`
};
delete fixtureEnv.PLAYWRIGHT_CHROMIUM_CHANNEL;

const fixture = JSON.parse(execFileSync('python3', ['-m', 'tests.history_browser_fixture'], {
  cwd: ROOT, env: fixtureEnv, encoding: 'utf8', maxBuffer: 4 * 1024 * 1024
}));

let chromium = null;
let launchError = null;
try {
  ({chromium} = require('playwright'));
} catch (error) {
  launchError = error;
}

let browser = null;
test.before(async () => {
  if (!chromium) return;
  try {
    browser = await chromium.launch({headless: true, channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL || undefined});
  } catch (error) {
    launchError = error;
  }
});
test.after(async () => {
  if (browser) await browser.close();
});

function requireBrowser() {
  if (!browser) {
    const detail = launchError && launchError.stack ? launchError.stack : String(launchError || 'playwright/chromium missing');
    throw new Error('UNEXECUTED: qualified Chromium/Playwright unavailable; parent reproduction uses NODE_PATH=$HOME/lanes/artifacts/paper-waves-01a1101f/browser-env/node_modules, PLAYWRIGHT_CHROMIUM_CHANNEL unset, python3 -m tests.history_browser_fixture. ' + detail);
  }
}

async function openWorkspace(t, options = {}) {
  requireBrowser();
  const page = await browser.newPage({viewport: options.viewport || {width: 1440, height: 1000}});
  page.setDefaultTimeout(4000);
  t.after(() => page.close());
  const search = options.search || 'view=history&market=JP&horizon=1m&basis=usd_unhedged&return_basis=price';
  await page.route('http://fixture.test/**', route => route.fulfill({
    contentType: 'text/html',
    body: '<!doctype html><html lang="en"><body>' + fixture.html + '</body></html>'
  }));
  await page.goto('http://fixture.test/intl.html?' + search);
  const files = options.scripts || ['intl_workspace_state.js', 'intl_workspace_scenario.js', 'intl_workspace.js'];
  for (const file of files) {
    await page.addScriptTag({content: fs.readFileSync(path.join(ROOT, 'templates', file), 'utf8')});
  }
  if (options.mount !== false) {
    await page.evaluate(config => {
      window.handle = IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'), config);
    }, fixture.config);
  }
  return page;
}

async function calculate(page, local = '5', fx = '-3') {
  await page.locator('[data-im-scenario-field="local"]').fill(local);
  await page.locator('[data-im-scenario-field="fx"]').fill(fx);
  await page.locator('[data-im-scenario-action="calculate"]').click();
}

function snapshot(page) {
  return page.evaluate(() => ({
    state: handle.getState(),
    issues: document.querySelector('[data-im-issues]').textContent,
    confirmHidden: document.querySelector('[data-im-scenario-confirm-context]').hidden,
    resetHidden: document.querySelector('[data-im-scenario-confirm-reset]').hidden,
    url: location.search,
    local: document.querySelector('#im-scenario-local').value,
    fx: document.querySelector('#im-scenario-fx').value
  }));
}

async function restoreQuery(page, query) {
  return page.evaluate(search => {
    history.pushState(null, '', location.pathname + search);
    window.dispatchEvent(new PopStateEvent('popstate'));
    return {
      state: handle.getState(),
      issues: document.querySelector('[data-im-issues]').textContent,
      confirmHidden: document.querySelector('[data-im-scenario-confirm-context]').hidden,
      resetHidden: document.querySelector('[data-im-scenario-confirm-reset]').hidden,
      url: location.search,
      local: document.querySelector('#im-scenario-local').value,
      fx: document.querySelector('#im-scenario-fx').value
    };
  }, query);
}

test('basis-only proposal texts distinguish original and candidate currency basis', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  const originBefore = await page.locator('[data-im-scenario-context]').innerText();
  await page.locator('[data-im-action="set_basis"]').selectOption('local');
  assert.equal((await page.evaluate(() => handle.getState())).currency_basis, 'usd_unhedged');
  assert.equal(await page.locator('[data-im-scenario-confirm-context]').isVisible(), true);
  const origin = await page.locator('[data-im-scenario-context]').innerText();
  const candidate = await page.locator('[data-im-scenario-candidate-context]').innerText();
  assert.equal(origin, originBefore);
  assert.notEqual(candidate, origin);
  assert.match(origin, /Research basis: USD · Unhedged/);
  assert.match(origin, /FX assumption: USD per local unit/);
  assert.match(candidate, /Research basis: Local currency/);
  assert.match(candidate, /FX assumption: USD per local unit/);
  assert.doesNotMatch(origin, /Research basis: Local currency/);
  await page.locator('[data-im-scenario-action="confirm_context"]').click();
  assert.equal((await page.evaluate(() => handle.getState())).currency_basis, 'local');
});

test('changing return horizon does not rewrite mounted observation scores', async t => {
  const page = await openWorkspace(t);
  const before = await page.locator('[data-im-history-market="JP"]').evaluate(node => node.textContent);
  assert.match(before, /0\.4375/);
  await page.locator('[data-im-action="set_horizon"]').selectOption('3m');
  const after = await page.locator('[data-im-history-market="JP"]').evaluate(node => node.textContent);
  assert.equal(after, before);
  assert.equal(await page.locator('[data-im-history-panel]').getAttribute('data-horizon'), '3m');
  assert.equal((await page.evaluate(() => handle.getState())).horizon, '3m');
});

test('calculate is reduced once from the native submit path', async t => {
  const page = await openWorkspace(t);
  await page.evaluate(() => {
    const original = IntlWorkspaceScenario.reduceDraft;
    window.__reduceTypes = [];
    IntlWorkspaceScenario.reduceDraft = function (draft, command, locale) {
      window.__reduceTypes.push(command && command.type);
      return original(draft, command, locale);
    };
  });
  await calculate(page);
  const types = await page.evaluate(() => window.__reduceTypes);
  const calculates = types.filter(type => type === 'calculate');
  assert.equal(calculates.length, 1);
  assert.match(await page.locator('[data-im-scenario-usd]').innerText(), /1\.85/);
});

test('tiny nonzero conditional return uses scientific notation instead of a rounded zero', async t => {
  const page = await openWorkspace(t);
  await calculate(page, '0.001', '0');
  const usd = await page.locator('[data-im-scenario-usd]').innerText();
  assert.match(usd, /e/i);
  assert.doesNotMatch(usd, /^0%$/);
});

test('missing scenario helper leaves the published fieldset disabled and history unmatched', async t => {
  const page = await openWorkspace(t, {scripts: ['intl_workspace_state.js', 'intl_workspace.js']});
  assert.equal(await page.locator('[data-im-scenario-fields]').evaluate(node => node.disabled), true);
  assert.equal(await page.locator('[data-im-history-panel]').evaluate(node => node.hidden), true);
  assert.equal(await page.locator('[data-im-unavailable]').evaluate(node => node.hidden), false);
  assert.equal(await page.locator('#im-scenario-local').isDisabled(), true);
});

test('unsupported restored view with a nonempty draft keeps the entire committed state and reports Unsupported value', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  const before = await snapshot(page);
  const result = await restoreQuery(page, '?view=not-a-view&market=JP&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group=');
  assert.deepEqual(result.state, before.state);
  assert.equal(result.confirmHidden, true);
  assert.equal(result.resetHidden, true);
  assert.equal(result.issues, 'Unsupported value');
  assert.equal(result.local, '5');
  assert.equal(result.fx, '-3');
  const pin = await page.evaluate(() => handle.dispatch({type: 'pin', market_id: 'KR'}));
  assert.equal(pin.ok, true);
  assert.deepEqual((await page.evaluate(() => handle.getState())).compare_markets, ['KR']);
});

test('malformed restored query with a nonempty draft reports Invalid URL state restored and does not stage confirmation', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  const before = await snapshot(page);
  const result = await restoreQuery(page, '?view=history&market=JP&not-a-field=1&horizon=1m&basis=usd_unhedged&return_basis=price&group=');
  assert.deepEqual(result.state, before.state);
  assert.equal(result.confirmHidden, true);
  assert.equal(result.issues, 'Invalid URL state restored');
  assert.equal(result.local, '5');
});

test('empty draft invalid popstate preserves committed state and does not adopt the parser initial workspace', async t => {
  const page = await openWorkspace(t);
  const before = await snapshot(page);
  assert.equal(before.local, '');
  const unsupported = await restoreQuery(page, '?view=not-a-view&market=JP&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group=');
  assert.deepEqual(unsupported.state, before.state);
  assert.equal(unsupported.confirmHidden, true);
  assert.equal(unsupported.issues, 'Unsupported value');
  const malformed = await restoreQuery(page, '?this-is-not-a-query');
  assert.deepEqual(malformed.state, before.state);
  assert.equal(malformed.confirmHidden, true);
  assert.equal(malformed.issues, 'Invalid URL state restored');
  assert.equal((await page.evaluate(() => handle.getState())).view, 'history');
  assert.equal((await page.evaluate(() => handle.getState())).selected_market, 'JP');
});

test('invalid popstate during pending confirmation keeps the origin tuple, restores the committed URL, and still requires confirm', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  await page.locator('[data-im-action="set_horizon"]').selectOption('3m');
  const pending = await snapshot(page);
  assert.equal(pending.confirmHidden, false);
  assert.equal(pending.state.horizon, '1m');
  const result = await restoreQuery(page, '?view=not-a-view&market=KR&pins=&horizon=12m&basis=local&return_basis=price&group=');
  assert.deepEqual(result.state, pending.state);
  assert.equal(result.confirmHidden, false);
  assert.equal(result.issues, 'Unsupported value');
  assert.match(result.url, /horizon=1m/);
  assert.doesNotMatch(result.url, /not-a-view/);
  const pin = await page.evaluate(() => handle.dispatch({type: 'pin', market_id: 'KR'}));
  assert.equal(pin.ok, false);
  await page.locator('[data-im-scenario-action="cancel_context"]').click();
  assert.equal((await page.evaluate(() => handle.getState())).horizon, '1m');
  assert.equal(await page.locator('#im-scenario-local').inputValue(), '5');
});

test('invalid popstate during reset keeps assumptions, reset confirmation, and the entire committed state', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  await page.locator('[data-im-scenario-action="request_reset"]').click();
  const pendingReset = await snapshot(page);
  assert.equal(pendingReset.resetHidden, false);
  const result = await restoreQuery(page, '?view=history&market=JP&pins=&horizon=&basis=usd_unhedged&return_basis=price&group=');
  assert.deepEqual(result.state, pendingReset.state);
  assert.equal(result.resetHidden, false);
  assert.equal(result.confirmHidden, true);
  assert.equal(result.issues, 'Invalid URL state restored');
  assert.equal(result.local, '5');
  await page.locator('[data-im-scenario-action="cancel_reset"]').click();
  assert.equal(await page.locator('#im-scenario-local').inputValue(), '5');
  assert.deepEqual(await page.evaluate(() => handle.getState()), pendingReset.state);
});

test('history market options use data-im-label-zh after document language changes', async t => {
  const page = await openWorkspace(t);
  await page.evaluate(() => {
    const option = document.querySelector('[data-im-history-panel] select[data-im-action="select_market"] option[value="JP"]');
    option.setAttribute('data-im-label-en', 'Japan market');
    option.setAttribute('data-im-label-zh', '日本市场');
    document.documentElement.lang = 'zh';
  });
  await page.waitForFunction(() => {
    const option = document.querySelector('[data-im-history-panel] select[data-im-action="select_market"] option[value="JP"]');
    return option && option.textContent === '日本市场';
  });
  const text = await page.locator('[data-im-history-panel] select[data-im-action="select_market"] option[value="JP"]').textContent();
  assert.equal(text, '日本市场');
});

test('pending basis review text follows document language without losing the original/candidate pair', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  await page.locator('[data-im-action="set_basis"]').selectOption('local');
  await page.evaluate(() => { document.documentElement.lang = 'zh'; });
  await page.waitForFunction(() => {
    const origin = document.querySelector('[data-im-scenario-context]').textContent;
    const candidate = document.querySelector('[data-im-scenario-candidate-context]').textContent;
    return origin.includes('研究口径：美元') && candidate.includes('研究口径：本币');
  });
  const origin = await page.locator('[data-im-scenario-context]').innerText();
  const candidate = await page.locator('[data-im-scenario-candidate-context]').innerText();
  assert.match(origin, /研究口径：美元 · 未对冲/);
  assert.match(candidate, /研究口径：本币/);
  assert.match(origin, /汇率假设：每单位本币兑美元/);
  assert.match(candidate, /汇率假设：每单位本币兑美元/);
  assert.notEqual(candidate, origin);
});

test('without a History draft the incumbent popstate path still stages the parsed result', async t => {
  const page = await openWorkspace(t, {scripts: ['intl_workspace_state.js', 'intl_workspace.js']});
  const before = await page.evaluate(() => handle.getState());
  assert.equal(before.view, 'history');
  const result = await page.evaluate(() => {
    history.pushState(null, '', location.pathname + '?view=not-a-view&market=JP&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group=');
    window.dispatchEvent(new PopStateEvent('popstate'));
    return {state: handle.getState(), issues: document.querySelector('[data-im-issues]').textContent};
  });
  assert.equal(result.issues, 'Unsupported value');
  assert.notDeepEqual(result.state, before);
  assert.equal(result.state.view, 'overview');
  assert.equal(result.state.selected_market, null);
});

test('resize is admitted during pending confirmation while pin and view remain refused', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  await page.locator('[data-im-action="set_horizon"]').selectOption('3m');
  const resize = await page.evaluate(() => handle.dispatch({type: 'resize'}));
  const pin = await page.evaluate(() => handle.dispatch({type: 'pin', market_id: 'KR'}));
  const view = await page.evaluate(() => handle.dispatch({type: 'set_view', view: 'overview'}));
  assert.equal(resize.ok, true);
  assert.equal(pin.ok, false);
  assert.equal(view.ok, false);
  assert.equal((await page.evaluate(() => handle.getState())).horizon, '1m');
  assert.equal(await page.locator('[data-im-scenario-confirm-context]').isVisible(), true);
  assert.equal(await page.locator('[data-im-history-panel]').isVisible(), true);
});

test('replaceSource without rewriting generation attributes invalidates the old history panel and keeps raw inputs', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  const fresh = 'im-workspace-generation:99999999-9999-4999-8999-999999999999';
  const result = await page.evaluate(source => {
    const old = handle.getState().source_reference;
    return handle.replaceSource(source, old);
  }, fresh);
  assert.equal(result.ok, true);
  assert.equal(await page.locator('[data-im-history-panel]').evaluate(node => node.hidden), true);
  assert.equal(await page.locator('[data-im-unavailable]').evaluate(node => node.hidden), false);
  assert.equal(await page.locator('#im-scenario-local').inputValue(), '5');
});

test('unknown KR roster slot is shown as qualified-history-unavailable, not as an empty success', async t => {
  const page = await openWorkspace(t);
  await page.locator('[data-im-history-panel] [data-im-action="select_market"]').selectOption('KR');
  assert.equal(await page.locator('[data-im-history-market="KR"]').isVisible(), true);
  assert.match(await page.locator('[data-im-history-market="KR"] [data-im-history-status]').innerText(), /Qualified history unavailable|暂无符合条件的历史/);
  assert.equal(await page.locator('[data-im-history-market="KR"] table').count(), 0);
});

test('empty draft adopts a basis change immediately without confirmation', async t => {
  const page = await openWorkspace(t);
  await page.locator('[data-im-action="set_basis"]').selectOption('local');
  assert.equal(await page.locator('[data-im-scenario-confirm-context]').isVisible(), false);
  assert.equal((await page.evaluate(() => handle.getState())).currency_basis, 'local');
});

test('overview regression: same controller hides history, keeps pins, and restores the blank-unrelated draft', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  await page.evaluate(() => handle.dispatch({type: 'pin', market_id: 'KR'}));
  await page.evaluate(() => handle.dispatch({type: 'set_view', view: 'overview'}));
  const state = await page.evaluate(() => handle.getState());
  assert.equal(state.view, 'overview');
  assert.deepEqual(state.compare_markets, ['KR']);
  assert.equal(await page.locator('[data-im-history-panel]').isVisible(), false);
  assert.equal(await page.locator('[data-view="overview"]:not([hidden])').count(), 1);
  await page.evaluate(() => handle.dispatch({type: 'set_view', view: 'history'}));
  assert.equal(await page.locator('#im-scenario-local').inputValue(), '5');
  assert.equal(await page.locator('[data-im-scenario-result]').isVisible(), true);
});

test('candidate edits during pending do not become origin raw until confirm; cancel restores the calculated pair', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  await page.locator('[data-im-action="set_horizon"]').selectOption('3m');
  await page.locator('#im-scenario-local').fill('12');
  await page.locator('#im-scenario-fx').fill('4');
  assert.equal(await page.locator('[data-im-scenario-result]').isVisible(), false);
  await page.locator('[data-im-scenario-action="cancel_context"]').click();
  assert.equal(await page.locator('#im-scenario-local').inputValue(), '5');
  assert.equal(await page.locator('#im-scenario-fx').inputValue(), '-3');
  assert.equal((await page.evaluate(() => handle.getState())).horizon, '1m');
  assert.equal(await page.locator('[data-im-scenario-result]').isVisible(), true);
});

test('nested workspace submit cannot calculate the owning draft', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  await page.evaluate(() => {
    const nested = document.createElement('section');
    nested.setAttribute('data-im-workspace', '');
    nested.innerHTML = '<form data-im-scenario-form><input data-im-scenario-field="local" value="99"><button type="submit" data-im-scenario-action="calculate">x</button></form>';
    document.querySelector('[data-im-history-panel]').appendChild(nested);
    nested.querySelector('form').dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
  });
  assert.equal(await page.locator('#im-scenario-local').inputValue(), '5');
  assert.equal(await page.locator('[data-im-scenario-result]').isVisible(), true);
});

test('destroy restores blank disabled fallback and a new mount starts blank', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  await page.evaluate(() => handle.destroy());
  assert.equal(await page.locator('#im-scenario-local').inputValue(), '');
  assert.equal(await page.locator('[data-im-scenario-fields]').evaluate(el => el.disabled), true);
  assert.equal(await page.locator('#im-scenario-local').isDisabled(), true);
  await page.evaluate(c => {
    window.handle = IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'), c);
  }, fixture.config);
  assert.equal(await page.locator('#im-scenario-local').inputValue(), '');
});

test('Escape cancels staged context and restores focus to the initiating control', async t => {
  const page = await openWorkspace(t);
  await calculate(page);
  await page.locator('[data-im-action="set_horizon"]').selectOption('3m');
  await page.locator('#im-scenario-local').press('Escape');
  assert.equal(await page.locator('[data-im-scenario-confirm-context]').isVisible(), false);
  assert.equal((await page.evaluate(() => handle.getState())).horizon, '1m');
  assert.equal(await page.evaluate(() => document.activeElement.getAttribute('data-im-action')), 'set_horizon');
});

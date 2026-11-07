#!/usr/bin/env node
/* Declared synthetic Brain inspector freshness fixture.
 * Serves the complete widget source over loopback, intercepts
 * /api/brain/me, /api/brain/threads, /api/brain/stream as a labeled
 * stub SSE transport, and drives public MMBrain.open + composer send.
 * Not a live backend, model, or account call.
 */
'use strict';

const fs = require('fs');
const http = require('http');
const path = require('path');
const { pathToFileURL } = require('url');

const ROOT = path.resolve(__dirname, '../..');
const ART = path.join(ROOT, 'artifacts');
const LOGS = path.join(ART, 'logs');
const SHOTS = path.join(ART, 'screenshots');
const PLAYWRIGHT_ROOT =
  '/home/ubuntu2/lanes/tmp/terminal-audit20-A03-save-implementation-01a10f92/terminal/node_modules/playwright';
const CHROME =
  '/home/ubuntu2/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome';

const ASSETS = {
  baseline: path.join(ART, 'owner-preimage', 'mm_brain.js'),
  repaired: path.join(ROOT, 'site', 'mm_brain.js'),
};

const VIEWPORTS = [
  { name: 'desktop-1440x900', width: 1440, height: 900 },
  { name: 'tablet-820x1180', width: 820, height: 1180 },
  { name: 'mobile-390x844', width: 390, height: 844 },
];

const EXPECT_EN = {
  Price: { word: 'current', as_of: '2026-10-06', family: 'owner.quote', value: 'USD 187.5' },
  '1M return': { word: 'stale', as_of: '2026-09-01', family: 'owner.return', value: '12.3%' },
  '3M return': { word: 'unknown', as_of: '2026-07-01', family: 'owner.return', value: '4.1%' },
  '12M return': { word: 'unknown', as_of: '2025-10-06', family: 'owner.return', value: '18%' },
  Stage: { word: 'unknown', as_of: '2026-10-01', family: 'owner.stage', value: 'C' },
  'Weeks in stage': { word: 'unknown', as_of: '2026-10-01', family: 'owner.stage', value: '7' },
  'Industry rank': { word: 'unknown', as_of: '2026-10-01', family: 'owner.industry', value: '88 percentile' },
  'Relative strength': { word: 'unknown', as_of: '2026-10-01', family: 'owner.rs', value: '91 percentile' },
  'Next earnings': { word: 'not applicable', as_of: '2026-10-06', family: 'owner.earnings', value: '2026-11-15' },
  'EPS growth': { word: 'unknown', as_of: '2026-08-15', family: 'owner.earnings', value: '21%' },
  'Revenue growth': { word: 'unknown', as_of: '2026-08-14', family: 'owner.prototype', value: 'toString-safe' },
  'prototype.inherited.constructor': { word: 'unknown', as_of: '2026-08-13', family: 'owner.prototype', value: 'constructor-safe' },
  'prototype.inherited.proto': { word: 'unknown', as_of: '2026-08-12', family: 'owner.prototype', value: 'prototype-safe' },
  'prototype.inherited.own_key': { word: 'unknown', as_of: '2026-08-11', family: 'owner.prototype', value: 'own-key-safe' },
  Themes: { word: 'unknown', as_of: '<b>asof</b>', family: '<script>evil()</script>', value: '<img src=x onerror=alert(1)>, ok-theme' },
};

const EXPECT_ZH = {
  '价格': EXPECT_EN.Price,
  '1个月回报': EXPECT_EN['1M return'],
  '3个月回报': EXPECT_EN['3M return'],
  '12个月回报': EXPECT_EN['12M return'],
  '阶段': EXPECT_EN.Stage,
  '阶段周数': EXPECT_EN['Weeks in stage'],
  '行业排名': Object.assign({}, EXPECT_EN['Industry rank'], { value: '88 分位' }),
  '相对强度': Object.assign({}, EXPECT_EN['Relative strength'], { value: '91 分位' }),
  '下次财报': EXPECT_EN['Next earnings'],
  '每股收益增长': EXPECT_EN['EPS growth'],
  '营收增长': EXPECT_EN['Revenue growth'],
  'prototype.inherited.constructor': EXPECT_EN['prototype.inherited.constructor'],
  'prototype.inherited.proto': EXPECT_EN['prototype.inherited.proto'],
  'prototype.inherited.own_key': EXPECT_EN['prototype.inherited.own_key'],
  '主题': EXPECT_EN.Themes,
};

const ZH_WORD = {
  current: '最新',
  stale: '较早',
  unknown: '未知',
  'not applicable': '不适用',
};

function factsForRole(role) {
  return [
    { field_id: 'market.price.last', status: 'available', value: 187.5, unit: 'USD', as_of: '2026-10-06', freshness: { state: 'fresh', policy: 'owner_native' }, source: { source_id: 'quote.v1', source_family: 'owner.quote' } },
    { field_id: 'market.return.1m', status: 'available', value: 12.3, unit: 'percent', as_of: '2026-09-01', freshness: { state: 'stale', policy: 'owner_native' }, source: { source_id: 'ret.v1', source_family: 'owner.return' } },
    { field_id: 'market.return.3m', status: 'available', value: 4.1, unit: 'percent', as_of: '2026-07-01', freshness: { state: 'unknown', policy: 'owner_native' }, source: { source_id: 'ret.v1', source_family: 'owner.return' } },
    { field_id: 'market.return.12m', status: 'available', value: 18, unit: 'percent', as_of: '2025-10-06', source: { source_id: 'ret.v1', source_family: 'owner.return' } },
    { field_id: 'stage.current', status: 'available', value: 'C', unit: 'stage_code', as_of: '2026-10-01', freshness: { state: null, policy: 'owner_native' }, source: { source_id: 'stage.v1', source_family: 'owner.stage' } },
    { field_id: 'stage.weeks_in_stage', status: 'available', value: 7, unit: 'weeks', as_of: '2026-10-01', freshness: { state: 'current', policy: 'owner_native' }, source: { source_id: 'stage.v1', source_family: 'owner.stage' } },
    { field_id: 'industry.rank.percentile', status: 'available', value: 88, unit: 'percentile', as_of: '2026-10-01', freshness: { state: 'future', policy: 'owner_native' }, source: { source_id: 'ind.v1', source_family: 'owner.industry' } },
    { field_id: 'security.industry_member.rs_percentile', status: 'available', value: 91, unit: 'percentile', as_of: '2026-10-01', freshness: { state: 1, policy: 'owner_native' }, source: { source_id: 'rs.v1', source_family: 'owner.rs' } },
    { field_id: 'earnings.next_date', status: 'available', value: '2026-11-15', unit: '', as_of: '2026-10-06', freshness: { state: 'not_applicable', policy: 'owner_native' }, source: { source_id: 'earn.v1', source_family: 'owner.earnings' } },
    { field_id: 'earnings.latest.eps_growth_pct', status: 'available', value: 21, unit: 'percent', as_of: '2026-08-15', freshness: { state: 'unsupported', policy: 'owner_native' }, source: { source_id: 'earn.v1', source_family: 'owner.earnings' } },
    { field_id: 'earnings.latest.revenue_growth_pct', status: 'available', value: 'toString-safe', unit: 'prototype_key', as_of: '2026-08-14', freshness: { state: 'toString', policy: 'owner_native' }, source: { source_id: 'proto.v1', source_family: 'owner.prototype' } },
    { field_id: 'prototype.inherited.constructor', status: 'available', value: 'constructor-safe', unit: 'prototype_key', as_of: '2026-08-13', freshness: { state: 'constructor', policy: 'owner_native' }, source: { source_id: 'proto.v2', source_family: 'owner.prototype' } },
    { field_id: 'prototype.inherited.proto', status: 'available', value: 'prototype-safe', unit: 'prototype_key', as_of: '2026-08-12', freshness: { state: '__proto__', policy: 'owner_native' }, source: { source_id: 'proto.v3', source_family: 'owner.prototype' } },
    { field_id: 'prototype.inherited.own_key', status: 'available', value: 'own-key-safe', unit: 'prototype_key', as_of: '2026-08-11', freshness: { state: 'hasOwnProperty', policy: 'owner_native' }, source: { source_id: 'proto.v4', source_family: 'owner.prototype' } },
    { field_id: 'theme.local.memberships', status: 'available', value: ['<img src=x onerror=alert(1)>', 'ok-theme'], unit: '', as_of: '<b>asof</b>', freshness: { state: 'unknown', policy: 'owner_native' }, source: { source_id: 'theme.v1', source_family: '<script>evil()</script>' } },
  ];
}

function sseBody(originId, revision, role) {
  const receipt = {
    type: 'context_receipt',
    request_id: 'fixture-req-1',
    origin: { origin_id: originId, context_revision: revision },
    effective_context: { source: 'active', entities: [{ type: 'security', id: 'NVDA' }] },
    explicit_entities: [],
    pinned_context: [],
    active_selection: [{ type: 'security', id: 'NVDA' }],
    ambient_widget_context: { symbol: 'NVDA' },
    context_flags: {},
    unsupported: [],
  };
  const native = {
    schema: 'brain.native_fact_receipt.v1',
    route: 'instant/native-fact',
    facts: factsForRole(role),
  };
  const events = [
    { type: 'run', run_id: 'fixture-run-1', thread_id: 'fixture-thread-1' },
    { type: 'meta', thread_id: 'fixture-thread-1', quota: { lane: 'fast', remaining: 9, limit: 20, period: 'day' } },
    receipt,
    { type: 'delta', text: 'Fixture native-fact reply (declared synthetic SSE).' },
    {
      type: 'done',
      route: 'instant/native-fact',
      native_fact_receipt: native,
      context_receipt: receipt,
    },
  ];
  return events.map((e) => 'data: ' + JSON.stringify(e) + '\n\n').join('');
}

function hostHtml(role) {
  return `<!doctype html>
<html lang="en" data-lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Brain inspector freshness fixture — ${role}</title>
</head>
<body>
  <p id="fixture-banner">FIXTURE HOST. Stub SSE transport labeled x-mm-fixture-transport. Not live backend/model.</p>
  <script>
    window.MM_BRAIN_CFG = {
      principal: 'fixture-operator',
      api: '',
      page: 'dashboard',
      symbol: function () { return 'NVDA'; }
    };
  </script>
  <script src="/widget/${role}.js"></script>
</body>
</html>`;
}

function startServer() {
  const baselineJs = fs.readFileSync(ASSETS.baseline);
  const repairedJs = fs.readFileSync(ASSETS.repaired);
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    if (url.pathname === '/widget/baseline.js') {
      res.writeHead(200, { 'content-type': 'application/javascript; charset=utf-8', 'cache-control': 'no-store' });
      res.end(baselineJs);
      return;
    }
    if (url.pathname === '/widget/repaired.js') {
      res.writeHead(200, { 'content-type': 'application/javascript; charset=utf-8', 'cache-control': 'no-store' });
      res.end(repairedJs);
      return;
    }
    if (url.pathname === '/' || url.pathname === '/index.html') {
      const role = url.searchParams.get('role') === 'baseline' ? 'baseline' : 'repaired';
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' });
      res.end(hostHtml(role));
      return;
    }
    res.writeHead(404, { 'content-type': 'text/plain', 'x-mm-fixture-transport': 'declared-synthetic-stub' });
    res.end('fixture-miss ' + url.pathname);
  });
  return new Promise((resolve, reject) => {
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      resolve({ server, port, origin: 'http://127.0.0.1:' + port });
    });
    server.on('error', reject);
  });
}

async function installApiStub(page, role) {
  const seen = { me: 0, threads: 0, stream: 0, other: [] };
  await page.route('**/api/brain/**', async (route) => {
    const req = route.request();
    const u = new URL(req.url());
    const headers = {
      'x-mm-fixture-transport': 'declared-synthetic-sse-stub',
      'cache-control': 'no-store',
    };
    if (u.pathname === '/api/brain/me') {
      seen.me += 1;
      await route.fulfill({
        status: 200,
        headers: { ...headers, 'content-type': 'application/json' },
        body: JSON.stringify({
          tier: 'pro',
          quotas: {
            fast: { remaining: 10, limit: 20, period: 'day' },
            pro: { remaining: 5, limit: 10, period: 'day' },
          },
        }),
      });
      return;
    }
    if (u.pathname === '/api/brain/threads') {
      seen.threads += 1;
      await route.fulfill({
        status: 200,
        headers: { ...headers, 'content-type': 'application/json' },
        body: JSON.stringify({ threads: [] }),
      });
      return;
    }
    if (u.pathname === '/api/brain/stream' && req.method() === 'POST') {
      seen.stream += 1;
      let originId = 'missing-origin';
      let revision = 0;
      try {
        const posted = req.postDataJSON() || {};
        const ai = (posted.context && posted.context.ai_context) || {};
        if (typeof ai.origin_id === 'string' && ai.origin_id) originId = ai.origin_id;
        if (typeof ai.context_revision === 'number') revision = ai.context_revision;
      } catch (e) {}
      await route.fulfill({
        status: 200,
        headers: { ...headers, 'content-type': 'text/event-stream; charset=utf-8' },
        body: sseBody(originId, revision, role),
      });
      return;
    }
    seen.other.push(req.method() + ' ' + u.pathname);
    await route.fulfill({
      status: 404,
      headers: { ...headers, 'content-type': 'application/json' },
      body: JSON.stringify({ fixture: true, error: 'unhandled-brain-path', path: u.pathname }),
    });
  });
  return seen;
}

function freshnessWordFromFr(fr, asOf) {
  const parts = String(fr || '').split(' · ');
  if (asOf && parts[0] === asOf) return parts[1] || '';
  return parts[0] || '';
}

async function readInspector(page) {
  return page.evaluate(() => {
    const insp = document.getElementById('mmb-ctxinsp');
    const body = document.getElementById('mmb-ctxinsp-body');
    const facts = Array.prototype.map.call(body.querySelectorAll('.mmb-ctxinsp-fact'), (row) => {
      const k = row.querySelector('.k');
      const v = row.querySelector('.v');
      const fr = row.querySelector('.fr');
      return {
        label: k ? k.textContent : '',
        value: v ? v.textContent : '',
        fr: fr ? fr.textContent : '',
        hostile_nodes: row.querySelectorAll('script,img,b').length,
        innerHTML: row.innerHTML,
      };
    });
    return {
      inspector_open: insp && insp.classList.contains('on'),
      aria_hidden: insp ? insp.getAttribute('aria-hidden') : null,
      fact_count: facts.length,
      facts,
      body_text: body ? body.textContent : '',
      widget_mounted: !!(window.MMBrain && window.MMBrain.mounted),
    };
  });
}

async function driveInspector(page, origin, role, viewport, lang) {
  await page.setViewportSize({ width: viewport.width, height: viewport.height });
  await page.goto(origin + '/?role=' + role, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForFunction(() => window.MMBrain && window.MMBrain.mounted, null, { timeout: 15000 });
  await page.evaluate(() => window.MMBrain.open());
  await page.waitForSelector('#mmb-panel.open', { timeout: 15000 });
  await page.waitForSelector('#mmb-ta', { state: 'visible', timeout: 15000 });
  if (lang === 'zh') {
    await page.evaluate(() => document.documentElement.setAttribute('data-lang', 'zh'));
  }
  await page.fill('#mmb-ta', 'What is NVDA last price?');
  await page.waitForFunction(() => {
    const b = document.getElementById('mmb-send');
    return b && !b.disabled;
  }, null, { timeout: 10000 });
  await page.click('#mmb-send');
  await page.waitForFunction(() => {
    const live = document.getElementById('mmb-live');
    return live && /Reply finished|回复完成/.test(live.textContent || '');
  }, null, { timeout: 20000 });
  await page.waitForSelector('.mmb-ctx.on [data-act="ctx-toggle"]', { timeout: 10000 });
  await page.click('.mmb-ctx.on [data-act="ctx-toggle"]');
  await page.waitForSelector('#mmb-ctxinsp.on', { timeout: 10000 });
  await page.waitForSelector('.mmb-ctxinsp-fact', { timeout: 10000 });
  const snap = await readInspector(page);
  const shotName = [role, viewport.name, lang].join('_') + '.png';
  const shotPath = path.join(SHOTS, shotName);
  try {
    await page.locator('#mmb-ctxinsp-card, .mmb-ctxinsp-card').first().screenshot({ path: shotPath });
    snap.screenshot = shotName;
  } catch (e) {
    snap.screenshot_error = String(e && e.message ? e.message : e);
  }
  snap.lang = lang;
  snap.role = role;
  snap.viewport = viewport.name;
  snap.page_url = page.url();
  return snap;
}

function checkBaseline(snap) {
  const failures = [];
  if (!snap.inspector_open) failures.push('inspector_not_open');
  if (snap.fact_count !== 15) failures.push('expected_fifteen_facts');
  const labels = ['3M return', '12M return', 'Stage', 'Weeks in stage', 'Industry rank', 'Relative strength', 'EPS growth', 'Revenue growth', 'prototype.inherited.constructor', 'prototype.inherited.proto', 'prototype.inherited.own_key', 'Themes'];
  labels.forEach((label) => {
    const row = (snap.facts || []).find((f) => f.label === label);
    if (!row) { failures.push('missing_row:' + label); return; }
    const word = freshnessWordFromFr(row.fr, row.fr.split(' · ')[0]);
    if (word !== 'current') failures.push(label + ':word=' + word + ':want_current_preimage');
  });
  return { ok: failures.length === 0, failures, expected_counterexample: 'exact PR8526 head53a labels unknown, missing, null, unsupported, and inherited-key states current' };
}

function checkRepaired(snap, lang) {
  const failures = [];
  const expect = lang === 'zh' ? EXPECT_ZH : EXPECT_EN;
  if (!snap.inspector_open) failures.push('inspector_not_open');
  const byLabel = {};
  (snap.facts || []).forEach((f) => { byLabel[f.label] = f; });
  Object.keys(expect).forEach((label) => {
    const exp = expect[label];
    const row = byLabel[label];
    if (!row) {
      failures.push('missing_row:' + label);
      return;
    }
    const want = lang === 'zh' ? ZH_WORD[exp.word] : exp.word;
    const word = freshnessWordFromFr(row.fr, exp.as_of);
    if (word !== want) failures.push(label + ':word=' + word + ':want=' + want);
    if (row.value !== exp.value) failures.push(label + ':value=' + row.value + ':want=' + exp.value);
    if (exp.as_of && !row.fr.includes(exp.as_of)) failures.push(label + ':as_of_missing');
    if (exp.family && !row.fr.includes(exp.family)) failures.push(label + ':family_missing');
    if (label === 'Themes' || label === '主题') {
      if (row.hostile_nodes !== 0) failures.push(label + ':hostile_nodes=' + row.hostile_nodes);
      if (/<script>|<img /i.test(row.innerHTML) && row.innerHTML.indexOf('&lt;') === -1) {
        failures.push(label + ':unescaped_html');
      }
    }
    if (exp.word !== 'current' && want !== '最新' && (word === 'current' || word === '最新')) {
      failures.push(label + ':unknown_lied_as_current');
    }
  });
  const aliasRow = byLabel[lang === 'zh' ? '阶段周数' : 'Weeks in stage'];
  if (aliasRow) {
    const w = freshnessWordFromFr(aliasRow.fr, '2026-10-01');
    if (w === 'current' || w === '最新') failures.push('alias_current_granted_as_fresh');
  }
  return { ok: failures.length === 0, failures, fact_count: snap.fact_count };
}

async function main() {
  fs.mkdirSync(LOGS, { recursive: true });
  fs.mkdirSync(SHOTS, { recursive: true });
  const started = new Date().toISOString();
  const result = {
    fixture: 'inspector_freshness_fixture',
    transport: 'declared-synthetic-sse-stub',
    chrome: CHROME,
    started,
    cases: [],
    ok: false,
  };
  if (!fs.existsSync(CHROME)) throw new Error('missing locked chromium-1228: ' + CHROME);
  if (!fs.existsSync(ASSETS.baseline) || !fs.existsSync(ASSETS.repaired)) {
    throw new Error('missing widget assets');
  }
  const { chromium } = require(PLAYWRIGHT_ROOT);
  const loop = await startServer();
  result.origin = loop.origin;
  result.server_port = loop.port;
  let browser;
  try {
    browser = await chromium.launch({
      executablePath: CHROME,
      headless: true,
      args: ['--no-sandbox', '--disable-dev-shm-usage'],
    });
    const version = browser.version();
    result.browser_version = version;

    const baselineCtx = await browser.newContext({ viewport: VIEWPORTS[0] });
    const baselinePage = await baselineCtx.newPage();
    const baselineSeen = await installApiStub(baselinePage, 'baseline');
    const baselineSnap = await driveInspector(baselinePage, loop.origin, 'baseline', VIEWPORTS[0], 'en');
    const baselineCheck = checkBaseline(baselineSnap);
    result.cases.push({
      id: 'owner53a_unknown_falsely_current',
      role: 'baseline',
      lang: 'en',
      viewport: VIEWPORTS[0].name,
      api_seen: baselineSeen,
      snap: baselineSnap,
      check: baselineCheck,
      executed: true,
      ok: baselineCheck.ok,
    });
    await baselineCtx.close();

    for (const viewport of VIEWPORTS) {
      const langs = viewport.name === 'desktop-1440x900' ? ['en', 'zh'] : ['en'];
      for (const lang of langs) {
        const ctx = await browser.newContext({ viewport });
        const page = await ctx.newPage();
        const seen = await installApiStub(page, 'repaired');
        const snap = await driveInspector(page, loop.origin, 'repaired', viewport, lang);
        const check = checkRepaired(snap, lang);
        result.cases.push({
          id: 'repaired_' + viewport.name + '_' + lang,
          role: 'repaired',
          lang,
          viewport: viewport.name,
          api_seen: seen,
          snap,
          check,
          executed: true,
          ok: check.ok,
        });
        await ctx.close();
      }
    }
    result.ok = result.cases.every((c) => c.executed && c.ok);
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve, reject) => loop.server.close((err) => (err ? reject(err) : resolve())));
    result.server_stopped = true;
    result.finished = new Date().toISOString();
  }
  const outPath = path.join(ART, 'inspector-freshness-results.json');
  fs.writeFileSync(outPath, JSON.stringify(result, null, 2));
  const logPath = path.join(LOGS, 'fixture-summary.json');
  fs.writeFileSync(logPath, JSON.stringify({
    ok: result.ok,
    origin: result.origin,
    browser_version: result.browser_version,
    cases: result.cases.map((c) => ({
      id: c.id, ok: c.ok, executed: c.executed, failures: c.check && c.check.failures, fact_count: c.snap && c.snap.fact_count,
    })),
  }, null, 2));
  if (!result.ok) {
    const failed = result.cases.filter((c) => !c.ok).map((c) => c.id + ':' + ((c.check && c.check.failures) || []).join(','));
    console.error('FIXTURE_FAIL ' + failed.join(' | '));
    process.exitCode = 1;
  } else {
    console.log('FIXTURE_OK cases=' + result.cases.length + ' origin=' + result.origin + ' chrome=' + result.browser_version);
  }
}

main().catch((err) => {
  const payload = { ok: false, executed: false, error: String(err && err.stack ? err.stack : err) };
  try { fs.writeFileSync(path.join(ART, 'inspector-freshness-results.json'), JSON.stringify(payload, null, 2)); } catch (e) {}
  console.error('FIXTURE_CRASH ' + payload.error);
  process.exit(2);
});

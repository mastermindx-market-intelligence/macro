// FIF PF r1 page suite (hermetic: no network, no browser).
//
// Pins the repair of the five defects the independent review found in the
// PF-1..PF-4 desk-page change:
// - R1 (F1/F5): the compare chain waits for the SELECTED issuer's health
//   answer (state.healthAnswer), so a company switch parks the chain in
//   loading instead of reading the previous issuer's answer and wrongly
//   showing no-records; every health request carries a sequence number and an
//   answer whose seq is not the current one is dropped even when its entity
//   matches the selection.
// - R2 (F2): in production the X-FIF-Dataset-Pointer header tells none
//   (no-records copy) from admitted (proceed) from anything else — a missing
//   pointer header, 'unavailable', admitted without a generation, or a failed
//   health fetch in any mode — which all show the existing 503 copy with its
//   Retry button; the catch path resets datasetMode and clears the fetch
//   lock; Retry with healthRetry re-issues health and resumes from
//   applyHealth, without it the button behaves exactly as before.
// - R5 (F5): after a failed health fetch, re-selecting the same issuer
//   re-issues health.
// - R6 (F6): an unparseable Latest value counts as absent (including
//   broad_source_at as source_snapshot_at, which then falls back to
//   recorded_at); instants compare at full precision beyond milliseconds; an
//   exact tie prefers admitted_at, then composed_state_at, then
//   broad_source_at; statement-column period dates are emitted as the same
//   YYYY-MM-DD strings the server's period parser accepts.
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const PAGE_SOURCE = readFileSync(new URL('../templates/fundamental_forensics.js', import.meta.url), 'utf8');
const BRIEFCASE_SOURCE = readFileSync(new URL('../templates/fif_saved_briefcase.js', import.meta.url), 'utf8');

const AAPL_ENTITY = 'ISS:US-XNAS-AAPL';
const MSFT_ENTITY = 'ISS:US-XNAS-MSFT';

function element() {
  const classes = new Set();
  const attrs = {};
  const listeners = {};
  return {
    classList: {
      add: (name) => classes.add(name),
      remove: (name) => classes.delete(name),
      contains: (name) => classes.has(name),
      toggle: (name, force) => {
        const on = force === undefined ? !classes.has(name) : !!force;
        if (on) classes.add(name); else classes.delete(name);
        return on;
      },
    },
    listeners,
    hidden: true,
    disabled: false,
    tabIndex: 0,
    innerHTML: '',
    textContent: '',
    value: '',
    placeholder: '',
    setAttribute: (key, value) => { attrs[key] = String(value); },
    removeAttribute: (key) => { delete attrs[key]; },
    getAttribute: (key) => (Object.prototype.hasOwnProperty.call(attrs, key) ? attrs[key] : null),
    addEventListener: (name, handler) => {
      listeners[name] = listeners[name] || [];
      listeners[name].push(handler);
    },
    removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    focus() {},
    click() {},
    scrollIntoView() {},
    insertAdjacentHTML() {},
  };
}

// A financial answer envelope the page's A38 digest check accepts.
function envelope(payload) {
  const body = Buffer.from(JSON.stringify(payload), 'utf8');
  return {
    body,
    sha256: createHash('sha256').update(body).digest('hex'),
  };
}

const QUERY_ENVELOPE = envelope({ receipt: { nodes: [] }, revisions: [], delivery: {} });

function statementsPayload() {
  // The production shape: statements repeat comparative columns; the page
  // de-duplicates them (PF-1) and emits the dates verbatim.
  return {
    statements: [
      {
        title: 'CONSOLIDATED STATEMENTS OF OPERATIONS',
        columns: [
          { label: 'FY2025', start: '2024-09-29', end: '2025-09-27' },
          { label: 'FY2024', start: '2023-10-01', end: '2024-09-28' },
          { label: 'FY2023', start: '2022-10-01', end: '2023-09-30' },
        ],
        rows: [],
      },
      {
        title: 'CONSOLIDATED BALANCE SHEETS',
        columns: [
          { label: 'As of 2024-09-28', start: '2023-10-01', end: '2024-09-28' },
          { label: 'As of 2023-09-30', start: '2022-10-01', end: '2023-09-30' },
          { label: 'As of 2022-09-30', start: '2021-10-01', end: '2022-09-28' },
        ],
        rows: [],
      },
    ],
  };
}

function companyPayload(symbol, entityId) {
  return {
    symbol,
    name: symbol + ' Inc.',
    entity_id: entityId,
    sector: 'Information Technology',
    latest_filed: '2025-02-03',
    latest_period: 'FY2024',
    periods: [{ fiscal_year: 2024, start: '2023-10-01', end: '2024-09-28' }],
    findings: [],
    coverage: {},
    disclosure_bundle: {
      tracks: [{
        status: 'ready',
        comparison: { note: 'fixture' },
        current_filing: { accession: '0000320193-25-000079' },
      }],
    },
  };
}

function pagePayload() {
  return {
    companies: {
      AAPL: companyPayload('AAPL', AAPL_ENTITY),
      MSFT: companyPayload('MSFT', MSFT_ENTITY),
    },
    default_symbol: 'AAPL',
    ranked_findings: [],
    generated_at: '2026-10-13T02:05:00Z',
  };
}

// One health answer: { ok: true, headers, body } | { ok: false, status } |
// { reject: true }. Builders below keep the header names exact.
function healthAnswer(clocks, generation, mode, pointer) {
  const headers = {};
  if (mode) headers['X-FIF-Financial-Dataset-Mode'] = mode;
  if (pointer) headers['X-FIF-Dataset-Pointer'] = pointer;
  if (generation) {
    headers['X-FIF-Dataset-Generation-Id'] = generation.id;
    headers['X-FIF-Dataset-Admitted-At'] = generation.admitted_at;
  }
  return {
    ok: true,
    headers,
    body: { schema: 'fundamental_forensics.health/v1', status: 'current', clocks: clocks || {} },
  };
}

const GOOD_CLOCKS = { broad_source_at: '2026-10-13T02:05:00Z' };

function admittedAnswer(entity, id) {
  return healthAnswer(
    GOOD_CLOCKS,
    { id: id || 'ffprods_gen2', admitted_at: '2026-10-13T02:00:00Z' },
    'production',
    'admitted'
  );
}

// options.healthRoute(url, index) -> an answer to settle immediately, or
// null/undefined to leave the call GATED until the test resolves
// healthCalls[index].settle(answer). options.queryStatus (value or thunk)
// fails every financial POST when truthy. The workspace listener is recorded
// so delegated clicks can be fired for real.
function harness(options) {
  options = options || {};
  const fetchCalls = [];
  const healthCalls = [];
  const nodes = {};
  for (const id of [
    'ff-evidence', 'ff-evidence-body', 'ff-evidence-title', 'ff-evidence-close',
    'ff-workspace', 'ff-scrim', 'ff-run-meta', 'ff-freshness-status', 'ff-as-of',
    'ff-source-snapshot', 'ff-source-label', 'ff-desk-stamp', 'ff-main', 'ff-gate',
    'ff-gate-state', 'ff-view-status', 'ff-saved-controls', 'ff-saved-select',
    'ff-saved-name', 'ff-saved-save', 'ff-saved-rename', 'ff-saved-delete',
    'ff-saved-badge', 'ff-saved-notice', 'ff-peer-save-row', 'ff-peer-save',
    'ff-asof-latest', 'ff-asof-input', 'ff-revisions-table', 'ff-statements',
    'ff-compare-grid', 'ff-tabs', 'ff-company-identity'
  ]) nodes[id] = element();
  const windowListeners = {};
  const pushes = [];
  const location = {
    hostname: 'contract.test',
    pathname: '/fundamental_forensics.html',
    search: '',
    hash: ''
  };
  const storageMap = new Map();
  const storage = {
    get: (key) => (storageMap.has(key) ? storageMap.get(key) : null),
    set: (key, value) => { storageMap.set(key, String(value)); },
    getItem: (key) => (storageMap.has(key) ? storageMap.get(key) : null),
    setItem: (key, value) => { storageMap.set(key, String(value)); },
  };
  const documentObject = {
    readyState: 'loading',
    addEventListener() {},
    getElementById: (id) => nodes[id] || element(),
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement: () => element(),
    body: { classList: { add() {}, remove() {} }, appendChild() {}, removeChild() {} },
    documentElement: { getAttribute() { return 'en'; } },
    activeElement: null,
  };

  function buildHealthResponse(answer) {
    if (answer.reject) return Promise.reject(new Error('health network failure'));
    if (answer.ok === false) {
      return Promise.resolve({
        ok: false,
        status: answer.status || 500,
        headers: { get: () => '' },
        text: () => Promise.resolve(answer.text || ''),
      });
    }
    return Promise.resolve({
      ok: true,
      headers: { get: (name) => (answer.headers && answer.headers[name]) || '' },
      json: () => Promise.resolve(JSON.parse(JSON.stringify(answer.body))),
    });
  }

  function queryStatus() {
    return typeof options.queryStatus === 'function' ? options.queryStatus() : (options.queryStatus || 0);
  }

  function responseFor(url, init) {
    const text = init && init.body ? String(init.body) : '';
    fetchCalls.push({ url: String(url), body: text, method: init && init.method });
    if (String(url).indexOf('/api/forensics/health') >= 0) {
      const gate = { index: healthCalls.length, url: String(url) };
      gate.promise = new Promise((resolve) => { gate.settle = (answer) => resolve(answer); });
      healthCalls.push(gate);
      const immediate = options.healthRoute ? options.healthRoute(String(url), gate.index) : null;
      if (immediate) gate.settle(immediate);
      return gate.promise.then(buildHealthResponse);
    }
    if (String(url).indexOf('/api/forensics/v1/financial/statements') >= 0) {
      const packed = envelope(options.statements || statementsPayload());
      return Promise.resolve({
        ok: true,
        headers: { get: (name) => (name === 'X-FIF-Response-SHA256' ? packed.sha256 : '') },
        arrayBuffer: () => Promise.resolve(packed.body.buffer.slice(
          packed.body.byteOffset, packed.body.byteOffset + packed.body.byteLength
        )),
      });
    }
    const status = queryStatus();
    if (status) {
      return Promise.resolve({
        ok: false,
        status,
        headers: { get: () => '' },
        text: () => Promise.resolve('{"detail":"financial query temporarily unavailable"}'),
      });
    }
    return Promise.resolve({
      ok: true,
      headers: { get: (name) => (name === 'X-FIF-Response-SHA256' ? QUERY_ENVELOPE.sha256 : '') },
      arrayBuffer: () => Promise.resolve(QUERY_ENVELOPE.body.buffer.slice(
        QUERY_ENVELOPE.body.byteOffset, QUERY_ENVELOPE.body.byteOffset + QUERY_ENVELOPE.body.byteLength
      )),
    });
  }
  const windowObject = {
    location,
    localStorage: storage,
    matchMedia: () => ({ matches: true, addEventListener() {}, addListener() {} }),
    __FF_WORKBENCH_TEST__: true,
    requestAnimationFrame(fn) { fn(); },
    setTimeout(fn) { fn(); },
    addEventListener: (name, handler) => {
      windowListeners[name] = windowListeners[name] || [];
      windowListeners[name].push(handler);
    },
    history: {
      pushState: (state, title, url) => { pushes.push(String(url)); location.search = String(url).replace(/^[^?]*/, '') || ''; },
      replaceState: (state, title, url) => { location.search = String(url).replace(/^[^?]*/, '') || ''; },
    },
    fetch: (url, init) => responseFor(url, init),
    URL,
    URLSearchParams,
    TextDecoder,
    crypto: webcrypto,
  };
  const context = vm.createContext({
    window: windowObject,
    document: documentObject,
    console,
    URL,
    URLSearchParams,
    TextDecoder,
    fetch: windowObject.fetch,
    crypto: webcrypto,
  });
  vm.runInContext(BRIEFCASE_SOURCE, context, { filename: 'fif_saved_briefcase.js' });
  vm.runInContext(PAGE_SOURCE, context, { filename: 'fundamental_forensics.js' });
  const api = windowObject.__FF_WORKBENCH_TEST__;
  api.cacheUi();
  api.ui.siteNav = element();
  api.ui.evidence = nodes['ff-evidence'];
  api.ui.workspace = nodes['ff-workspace'];
  api.ui.scrim = nodes['ff-scrim'];
  api.ui.main = nodes['ff-main'];
  api.ui.runMeta = nodes['ff-run-meta'];
  api.ui.tabs = [];
  api.state.payload = pagePayload();
  api.state.symbol = 'AAPL';
  api.state.access = 'open';
  api.bindEvents();
  function fireWorkspaceClick(selector) {
    const handlers = (nodes['ff-workspace'].listeners.click || []).slice();
    assert.ok(handlers.length >= 1, 'the delegated workspace click handler is bound');
    for (const handler of handlers) {
      handler({
        target: {
          closest: (candidate) => (candidate === selector ? { getAttribute: () => '' } : null)
        }
      });
    }
  }
  return { api, nodes, windowListeners, pushes, location, storage, fetchCalls, healthCalls, fireWorkspaceClick };
}

async function settle() {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1));
  }
}

function financialPosts(drive) {
  return drive.fetchCalls.filter((call) => call.url.indexOf('/api/forensics/v1/financial/') >= 0);
}

function postsForEntity(drive, entityId) {
  return financialPosts(drive).filter((call) => {
    try {
      return JSON.parse(call.body).entity_id === entityId;
    } catch (_error) {
      return false;
    }
  });
}

// ── R1: the company-switch race ─────────────────────────────────────────────

test('PF r1 R1: a company switch never shows no-records while the new issuer’s health is in flight', async () => {
  const drive = harness({
    healthRoute: (url) => (url.indexOf(encodeURIComponent('ISS:US-XNAS-AAPL')) >= 0
      ? admittedAnswer('AAPL', 'ffprods_aapl')
      : null), // MSFT's health answer stays gated
  });
  await drive.api.loadHealth();
  await settle();
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(drive.api.state.financial.phase, 'ready', 'AAPL shows values first');
  assert.ok(postsForEntity(drive, AAPL_ENTITY).length >= 4);

  // Select MSFT while its health answer is still in flight.
  drive.api.setCompany('MSFT', false);
  assert.equal(drive.api.state.financial.phase, 'loading');
  assert.equal(drive.api.state.financial.awaitingHealth, true);
  let html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.doesNotMatch(html, /No filing records published yet/, 'the stale AAPL answer must not paint no-records');
  assert.doesNotMatch(html, /尚未发布申报记录/);
  await settle();
  html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.doesNotMatch(html, /No filing records published yet/, 'never, at any point');
  assert.equal(postsForEntity(drive, MSFT_ENTITY).length, 0, 'no query is sent while parked');

  // The answer arrives: the next financial request is MSFT's query.
  drive.healthCalls[1].settle(admittedAnswer('MSFT', 'ffprods_msft'));
  await settle();
  assert.equal(drive.api.state.financial.phase, 'ready');
  const msftPosts = postsForEntity(drive, MSFT_ENTITY);
  assert.ok(msftPosts.length >= 4, 'MSFT\'s own compare chain fires');
  const lastQuery = financialPosts(drive).filter((call) => call.url.indexOf('/financial/query') >= 0).pop();
  assert.equal(JSON.parse(lastQuery.body).entity_id, MSFT_ENTITY);
});

test('PF r1 R1: a stale-seq health answer is dropped even when its entity matches', async () => {
  const drive = harness({ healthRoute: () => null }); // every health call gated
  drive.api.setCompany('AAPL', false); // health call 0, seq 1
  drive.api.setCompany('MSFT', false); // health call 1, seq 2
  drive.api.setCompany('AAPL', false); // health call 2, seq 3 — two A requests in flight
  await settle();
  assert.equal(drive.healthCalls.length, 3);

  // The SECOND AAPL answer lands and applies.
  drive.healthCalls[2].settle(admittedAnswer('AAPL', 'ffprods_a2'));
  await settle();
  assert.equal(drive.api.state.health.generation.id, 'ffprods_a2');

  // B's answer is stale by seq.
  drive.healthCalls[1].settle(admittedAnswer('MSFT', 'ffprods_msft'));
  await settle();

  // The FIRST AAPL answer lands LAST: the entity matches the selection but
  // the seq is old — it must be dropped whole.
  drive.healthCalls[0].settle(admittedAnswer('AAPL', 'ffprods_a1'));
  await settle();
  assert.equal(drive.api.state.health.generation.id, 'ffprods_a2', 'an older answer cannot overwrite a newer one');
  assert.equal(drive.api.state.healthAnswer.seq, 3);
  assert.equal(drive.api.state.healthAnswer.entity_id, AAPL_ENTITY);
});

// ── R2: none versus unavailable ─────────────────────────────────────────────

test('PF r1 R2: pointer none keeps the no-records copy and sends no query', async () => {
  const drive = harness({
    healthRoute: () => healthAnswer(GOOD_CLOCKS, null, 'production', 'none'),
  });
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0);
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /No filing records published yet/);
  assert.match(html, /We have not published filing records for this company yet, so no vintage is shown\./);
  assert.match(html, /尚未发布申报记录/);
  assert.match(html, /我们尚未发布该公司的申报记录，因此不显示任何版本。/);
  assert.notEqual(drive.api.state.financial.healthRetry, true);
});

test('PF r1 R2: pointer unavailable shows the 503 copy with Retry, never no-records', async () => {
  const drive = harness({
    healthRoute: () => healthAnswer(GOOD_CLOCKS, null, 'production', 'unavailable'),
  });
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0);
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Data temporarily unavailable/);
  assert.match(html, /数据暂不可用/);
  assert.match(html, /data-financial-retry="1"/);
  assert.doesNotMatch(html, /No filing records published yet/);
  assert.equal(drive.api.state.financial.healthRetry, true);
});

test('PF r1 R2: pointer admitted without a generation shows the 503 copy', async () => {
  const drive = harness({
    healthRoute: () => healthAnswer(GOOD_CLOCKS, null, 'production', 'admitted'),
  });
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0);
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Data temporarily unavailable/);
  assert.doesNotMatch(html, /No filing records published yet/);
  assert.equal(drive.api.state.financial.healthRetry, true);
});

test('PF r1 R2: a missing pointer header in production shows the 503 copy', async () => {
  const drive = harness({
    healthRoute: () => healthAnswer(
      GOOD_CLOCKS,
      { id: 'ffprods_gen2', admitted_at: '2026-10-13T02:00:00Z' },
      'production',
      '' // header absent
    ),
  });
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0);
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Data temporarily unavailable/);
  assert.doesNotMatch(html, /No filing records published yet/);
  assert.equal(drive.api.state.financial.healthRetry, true);
});

test('PF r1 R2: a failed health fetch shows the 503 copy, resets datasetMode and clears the lock', async () => {
  let msftAnswer = { reject: true };
  const drive = harness({
    healthRoute: (url) => (url.indexOf(encodeURIComponent('ISS:US-XNAS-AAPL')) >= 0
      ? admittedAnswer('AAPL', 'ffprods_aapl')
      : msftAnswer),
  });
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(drive.api.state.datasetMode, 'production');
  assert.ok(postsForEntity(drive, AAPL_ENTITY).length >= 4);

  drive.api.setCompany('MSFT', false);
  await settle();
  assert.equal(drive.api.state.datasetMode, '', 'the catch path resets the mode');
  assert.equal(drive.api.state.healthRequestedFor, '', 'the fetch lock is cleared');
  assert.equal(drive.api.state.healthAnswer.ok, false);
  assert.equal(drive.api.state.healthAnswer.entity_id, MSFT_ENTITY);
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Data temporarily unavailable/);
  assert.match(html, /data-financial-retry="1"/);
  assert.doesNotMatch(html, /No filing records published yet/);
  assert.equal(postsForEntity(drive, MSFT_ENTITY).length, 0, 'no query after a failed health call');
  assert.equal(drive.api.state.financial.healthRetry, true);
});

test('PF r1 R2: Retry with healthRetry re-issues health and resumes from applyHealth', async () => {
  let msftAnswer = { reject: true };
  const drive = harness({
    healthRoute: (url) => (url.indexOf(encodeURIComponent('ISS:US-XNAS-AAPL')) >= 0
      ? admittedAnswer('AAPL', 'ffprods_aapl')
      : msftAnswer),
  });
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  drive.api.setCompany('MSFT', false);
  await settle();
  assert.equal(drive.api.state.financial.healthRetry, true);
  const healthBefore = drive.healthCalls.length;

  // The store comes back; Retry must re-issue HEALTH (not just the chain).
  msftAnswer = admittedAnswer('MSFT', 'ffprods_msft');
  drive.fireWorkspaceClick('[data-financial-retry]');
  assert.equal(drive.api.state.financial.phase, 'loading');
  assert.equal(drive.api.state.financial.awaitingHealth, true);
  await settle();
  assert.equal(drive.healthCalls.length, healthBefore + 1, 'health was re-issued');
  assert.ok(drive.healthCalls[healthBefore].url.indexOf(encodeURIComponent(MSFT_ENTITY)) >= 0);
  assert.equal(drive.api.state.financial.phase, 'ready', 'the chain resumes once the answer lands');
  assert.ok(postsForEntity(drive, MSFT_ENTITY).length >= 4);
});

test('PF r1 R2: Retry without healthRetry refreshes health, then the chain re-POSTs', async () => {
  const query = { status: 503 };
  const drive = harness({
    healthRoute: () => healthAnswer(GOOD_CLOCKS, null, 'golden', ''),
    queryStatus: () => query.status,
  });
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(drive.api.state.financial.phase, 'error');
  assert.equal(drive.api.state.financial.errorStatus, 503);
  assert.notEqual(drive.api.state.financial.healthRetry, true);

  const healthBefore = drive.healthCalls.length;
  const postsBefore = financialPosts(drive).length;
  query.status = 0; // the financial service recovers
  drive.fireWorkspaceClick('[data-financial-retry]');
  await settle();
  // PFM r1 (item 4): the compare-chain branch now refreshes health first,
  // so a superseded generation can recover — same shape as the healthRetry
  // branch, same copy in the panel.
  assert.equal(drive.healthCalls.length, healthBefore + 1, 'Retry refreshes health in both branches');
  assert.ok(financialPosts(drive).length > postsBefore, 'the chain re-POSTs after the health answer lands');
  assert.equal(drive.api.state.financial.phase, 'ready');
});

test('PF r1 R2: golden mode keeps today’s query behaviour, and a failed fetch still shows the 503 copy', async () => {
  let answer = healthAnswer(GOOD_CLOCKS, null, 'golden', '');
  const drive = harness({ healthRoute: () => answer });
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  assert.ok(postsForEntity(drive, AAPL_ENTITY).length >= 4, 'golden still queries');
  assert.notEqual(drive.api.state.financial.healthRetry, true);

  answer = { reject: true };
  drive.api.setCompany('MSFT', false);
  await settle();
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Data temporarily unavailable/, 'a failed fetch shows the 503 copy in any mode');
  assert.equal(drive.api.state.datasetMode, '');
  assert.equal(drive.api.state.financial.healthRetry, true);
  assert.equal(postsForEntity(drive, MSFT_ENTITY).length, 0);
});

// ── R5: the fetch lock ──────────────────────────────────────────────────────

test('PF r1 R5: after a failed health fetch, re-selecting the same issuer re-issues health', async () => {
  let answer = { reject: true };
  const drive = harness({ healthRoute: () => answer });
  drive.api.setTab('compare', false);
  await drive.api.loadHealth();
  await settle();
  assert.equal(drive.api.state.financial.healthRetry, true);
  assert.equal(drive.api.state.healthRequestedFor, '', 'failure clears the lock');

  answer = admittedAnswer('AAPL', 'ffprods_aapl');
  drive.api.setCompany('AAPL', false); // the SAME issuer, selected again
  await settle();
  assert.equal(drive.healthCalls.length, 2, 'the cleared lock lets the same issuer retry');
  assert.equal(drive.api.state.financial.phase, 'ready');
  assert.ok(postsForEntity(drive, AAPL_ENTITY).length >= 4);
});

// ── R6: the Latest cutoff nits ──────────────────────────────────────────────

test('PF r1 R6: an unparseable Latest value counts as absent, including source_snapshot_at', () => {
  const drive = harness();
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: { composed_state_at: '2026-10-12T01:00:00Z', broad_source_at: 'not-a-timestamp' },
  };
  const clocks = drive.api.policyClocks();
  assert.equal(clocks.recorded_at, '2026-10-12T01:00:00Z', 'the garbage value never wins recorded_at');
  assert.equal(clocks.source_snapshot_at, '2026-10-12T01:00:00Z', 'an unparseable broad_source_at falls back to recorded_at');

  drive.api.state.health = {
    clocks: { composed_state_at: 'garbage', broad_source_at: 'also garbage' },
  };
  const empty = drive.api.policyClocks();
  assert.equal(empty.recorded_at, '', 'with nothing parseable the honest empty cutoff shows');
  assert.equal(empty.source_snapshot_at, '');
});

test('PF r1 R6: sub-millisecond ordering decides the Latest cutoff', () => {
  const drive = harness();
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: { composed_state_at: '2026-10-12T01:00:00.000100Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-12T01:00:00.000900Z', entity_id: AAPL_ENTITY },
  };
  assert.equal(
    drive.api.policyClocks().recorded_at,
    '2026-10-12T01:00:00.000900Z',
    'a later sub-millisecond admission beats a millisecond-equal composed_state_at'
  );
});

test('PF r1 R6: an exact tie prefers admitted_at, then composed_state_at, then broad_source_at', () => {
  const drive = harness();

  // admitted_at ties composed_state_at: the generation's ORIGINAL string wins.
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: { composed_state_at: '2026-10-12T01:00:00Z', broad_source_at: '2026-10-10T00:00:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-12T01:00:00.000Z', entity_id: AAPL_ENTITY },
  };
  assert.equal(drive.api.policyClocks().recorded_at, '2026-10-12T01:00:00.000Z', 'admitted_at wins the tie');

  // composed_state_at ties broad_source_at (no generation in golden mode).
  drive.api.state.datasetMode = 'golden';
  drive.api.state.health = {
    clocks: { composed_state_at: '2026-10-12T01:00:00Z', broad_source_at: '2026-10-12T01:00:00.000000Z' },
  };
  assert.equal(drive.api.policyClocks().recorded_at, '2026-10-12T01:00:00Z', 'composed_state_at beats broad_source_at on a tie');
  assert.equal(drive.api.policyClocks().source_snapshot_at, '2026-10-12T01:00:00.000000Z', 'source_snapshot_at is still broad_source_at');

  // A three-way tie in production: recorded_at is admitted_at's string.
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: { composed_state_at: '2026-10-12T01:00:00.500Z', broad_source_at: '2026-10-12T01:00:00.5Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-12T01:00:00.500000Z', entity_id: AAPL_ENTITY },
  };
  assert.equal(drive.api.policyClocks().recorded_at, '2026-10-12T01:00:00.500000Z', 'admitted_at is the first tie preference');
});

test('PF r1 R6: statement-column periods are emitted as the YYYY-MM-DD strings the server’s parser accepts', async () => {
  const drive = harness({
    healthRoute: () => admittedAnswer('AAPL', 'ffprods_gen2'),
  });
  drive.api.setTab('statements', false);
  await settle();
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  const queries = financialPosts(drive).filter((call) => call.url.indexOf('/financial/query') >= 0);
  assert.ok(queries.length >= 1);
  const dates = new Set();
  for (const call of queries) {
    for (const period of JSON.parse(call.body).periods) {
      assert.match(period.start, /^\d{4}-\d{2}-\d{2}$/, 'start is a plain YYYY-MM-DD string');
      assert.match(period.end, /^\d{4}-\d{2}-\d{2}$/, 'end is a plain YYYY-MM-DD string');
      dates.add(period.start);
      dates.add(period.end);
    }
  }
  // The exact set the server's date.fromisoformat (query_service period
  // admission) accepts — pinned from the python side too.
  assert.deepEqual(Array.from(dates).sort(), [
    '2021-10-01', '2022-09-28', '2022-10-01', '2023-09-30',
    '2023-10-01', '2024-09-28', '2024-09-29', '2025-09-27',
  ]);
});

// ── PFM item 1: an empty entity id is never a match ─────────────────────────

test('PFM r1 1: a success-path answer issued with no entity id is dropped once a company becomes selected', async () => {
  const drive = harness({ healthRoute: () => null }); // gate every health answer
  // No company selected: the very first health fetch is issued with no entity_id.
  drive.api.state.symbol = '';
  const pending = drive.api.loadHealth();
  await settle();
  assert.equal(drive.healthCalls.length, 1);
  assert.equal(drive.healthCalls[0].url.indexOf('entity_id='), -1, 'no entity_id on the no-company request');

  // The user picks AAPL WITHOUT triggering a fresh health fetch (state.symbol
  // is changed directly; setCompany would have refetched and masked the bug).
  drive.api.state.symbol = 'AAPL';
  // Deliver the gated ''-entity answer to the in-flight request.
  drive.healthCalls[0].settle(admittedAnswer('', 'ffprods_init'));
  await pending;
  await settle();
  // The '' answer never becomes the desk's health.
  assert.equal(drive.api.state.healthAnswer, null, 'a "no entity" answer must not be accepted for any company');
  assert.equal(drive.api.state.health, undefined, 'no clock was recorded from the dropped answer');
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0, 'no financial query sent from the dropped answer');
});

test('PFM r1 1: a failure-path answer issued with no entity id is dropped once a company becomes selected', async () => {
  const drive = harness({ healthRoute: () => null });
  drive.api.state.symbol = '';
  const pending = drive.api.loadHealth();
  await settle();
  assert.equal(drive.healthCalls.length, 1);

  drive.api.state.symbol = 'AAPL';
  // A network failure: catch fires with no status. The closure-captured
  // entityId is ''. With the bug the failed answer would be recorded with
  // '' as the entity and the datasetMode reset would clear any prior state.
  drive.healthCalls[0].settle({ reject: true });
  await pending;
  await settle();
  assert.equal(drive.api.state.healthAnswer, null, 'a "no entity" failure must not be recorded for any company');
  // The datasetMode was never touched — the '' answer never reached the catch body.
  assert.equal(drive.api.state.datasetMode, '');
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0, 'no financial query sent from the dropped failure');
});

// ── PFM item 3: a health 401/403 is an access answer, not an outage ──────────

test('PFM r1 3: health 401 routes through the signin state, never the 503 copy', async () => {
  const drive = harness({
    healthRoute: () => ({ ok: false, status: 401, text: '{"detail":"unauthorized"}' }),
  });
  await drive.api.loadHealth();
  await settle();
  assert.equal(drive.api.state.access, 'signin', 'the same access phase the financial chain uses for 401');
  assert.equal(drive.api.state.healthAnswer.ok, false);
  assert.equal(drive.api.state.healthAnswer.status, 401);
  assert.equal(drive.api.state.healthAnswer.entity_id, AAPL_ENTITY);
  assert.equal(drive.api.state.healthAnswer.pointer, '');
  assert.equal(drive.api.state.datasetMode, '', 'the mode is reset exactly as for any failed fetch');
  assert.equal(drive.api.state.healthRequestedFor, '', 'the fetch lock is cleared exactly as today');
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0, 'no financial query for an access failure');
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.doesNotMatch(html, /Data temporarily unavailable/, 'no 503 copy for a 401');
  assert.doesNotMatch(html, /数据暂不可用/);
  assert.doesNotMatch(html, /data-financial-retry/, 'no Retry button for a 401');
  assert.doesNotMatch(html, /Revisions temporarily unavailable/, 'no compare-chain 503 copy either');
});

test('PFM r1 3: health 403 routes through the upgrade state, never the 503 copy', async () => {
  const drive = harness({
    healthRoute: () => ({ ok: false, status: 403, text: '{"detail":"plan upgrade required"}' }),
  });
  await drive.api.loadHealth();
  await settle();
  assert.equal(drive.api.state.access, 'upgrade');
  assert.equal(drive.api.state.healthAnswer.ok, false);
  assert.equal(drive.api.state.healthAnswer.status, 403);
  assert.equal(drive.api.state.datasetMode, '');
  assert.equal(drive.api.state.healthRequestedFor, '');
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0);
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.doesNotMatch(html, /Data temporarily unavailable/);
  assert.doesNotMatch(html, /data-financial-retry/);
  assert.doesNotMatch(html, /Revisions temporarily unavailable/);
});

test('PFM r1 3: health 503 keeps the existing 503 copy with Retry', async () => {
  const drive = harness({
    healthRoute: () => ({ ok: false, status: 503, text: '{"detail":"temporarily unavailable"}' }),
  });
  await drive.api.loadHealth();
  await settle();
  // 503 is not an access failure: the access phase stays open and the 503
  // copy with its Retry is exactly what the pre-PFM page already rendered.
  assert.equal(drive.api.state.access, 'open');
  assert.equal(drive.api.state.healthAnswer.ok, false);
  assert.equal(drive.api.state.datasetMode, '');
  assert.equal(drive.api.state.healthRequestedFor, '');
  drive.api.setTab('compare', false);
  await settle();
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Data temporarily unavailable/);
  assert.match(html, /data-financial-retry="1"/);
});

// ── PFM item 4: the compare-chain Retry refreshes health ─────────────────────

test('PFM r1 4: the compare-chain Retry refreshes health before any new financial query', async () => {
  const query = { status: 503 };
  // The clocks run earlier than the generation's admitted_at, so the latest
  // cutoff in production mode is the generation — letting the test prove
  // the new generation flows into policy.recorded_at.
  const STALE_CLOCKS = { broad_source_at: '2026-10-12T01:00:00Z', composed_state_at: '2026-10-12T01:00:00Z' };
  const OLD_GEN = { id: 'ffprods_gen1', admitted_at: '2026-10-13T01:00:00.000000Z' };
  const NEW_GEN = { id: 'ffprods_gen2', admitted_at: '2026-10-13T03:00:00.000000Z' };
  let nextAnswer = healthAnswer(STALE_CLOCKS, OLD_GEN, 'production', 'admitted');
  const drive = harness({
    healthRoute: () => nextAnswer,
    queryStatus: () => query.status,
  });
  await drive.api.loadHealth();
  drive.api.setTab('compare', false);
  await settle();
  // The first compare chain fails on every leg with 5xx; healthRetry is NOT
  // set because the failure was on the chain, not on health.
  assert.equal(drive.api.state.financial.phase, 'error');
  assert.equal(drive.api.state.financial.errorStatus, 503);
  assert.notEqual(drive.api.state.financial.healthRetry, true);
  assert.equal(drive.api.state.health.generation.id, 'ffprods_gen1');
  const healthBefore = drive.healthCalls.length;
  const postsBefore = financialPosts(drive).length;

  // The store now serves a newer generation; the financial service recovers.
  nextAnswer = healthAnswer(STALE_CLOCKS, NEW_GEN, 'production', 'admitted');
  query.status = 0;
  drive.fireWorkspaceClick('[data-financial-retry]');
  await settle();

  // Retry must have issued a health request BEFORE any new financial POST.
  assert.equal(drive.healthCalls.length, healthBefore + 1, 'the compare-chain branch now refreshes health');
  assert.ok(financialPosts(drive).length > postsBefore, 'the chain re-POSTs after the health answer lands');
  assert.equal(drive.api.state.health.generation.id, 'ffprods_gen2', 'the new generation flows into state');
  assert.equal(drive.api.state.financial.phase, 'ready');
  // The very next financial query carries the NEW generation's recorded_at —
  // not the stale gen1 — proving the refresh reached the chain.
  const nextQuery = financialPosts(drive).slice(postsBefore)[0];
  const nextBody = JSON.parse(nextQuery.body);
  assert.equal(nextBody.policy.recorded_at, NEW_GEN.admitted_at,
    'the new query carries the new generation\'s recorded_at, never the old one');
});

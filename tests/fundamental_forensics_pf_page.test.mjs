// FIF PF-1..PF-4 page suite (hermetic: no network, no browser).
//
// Pins:
// - PF-1: statement columns are de-duplicated by the server's
//   period_semantic_key mirror BEFORE they are stored, keeping the FIRST
//   column (label included) and first-seen order; the revisions request body
//   therefore carries no repeated period.
// - PF-2: financialPost attaches the parsed JSON detail; only `unknown entity`
//   keeps the identity copy, other 400s get the could-not-evaluate copy,
//   no-clocks gets the no-recorded-cutoff copy, 503s keep the retry copy; a
//   raw detail/slug/status is never rendered.
// - PF-3: the Latest cutoff is the max of {composed_state_at, the matching
//   issuer's generation admitted_at (production only), broad_source_at} with
//   source_snapshot_at = broad_source_at else recorded_at; a stale health
//   answer for a deselected company is dropped; reResolveSavedView uses the
//   same helper and no longer refuses as 'clocks' when it has a value.
// - PF-4: a picked day before the admitted day sends NO query and shows the
//   earlier-dates copy; the picker min is that day; production without a
//   generation sends no query and shows the no-records copy; golden mode and
//   a missing mode header keep today's behaviour.
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const PAGE_SOURCE = readFileSync(new URL('../templates/fundamental_forensics.js', import.meta.url), 'utf8');
const BRIEFCASE_SOURCE = readFileSync(new URL('../templates/fif_saved_briefcase.js', import.meta.url), 'utf8');
const FIXTURE_DIR = new URL('../tests/fixtures/fundamental_forensics/fif_saved_research/', import.meta.url);
const STORE_KEY = 'mastermind.filing_forensics.saved_research.v1';

const AAPL_ENTITY = 'ISS:US-XNAS-AAPL';
const MSFT_ENTITY = 'ISS:US-XNAS-MSFT';

function element() {
  const classes = new Set();
  const attrs = {};
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
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    focus() {},
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
  // Two statements sharing the 2024-09-28 period (the production shape: each
  // statement repeats the comparative columns), plus a later statement whose
  // copy of 2023-09-30 carries a DIFFERENT label — the first-seen label wins.
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

// The harness: stub DOM + a fetch that records every call and answers the
// forensics endpoints with digest-valid bytes. options.health shapes the
// health response (body + headers); options.healthDelay holds the health
// answer back so races can be driven deterministically.
function harness(options) {
  options = options || {};
  const fetchCalls = [];
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
  const tabsHost = element();
  tabsHost.tabs = [];
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
    querySelector() { return element(); },
    querySelectorAll() { return []; },
    createElement: () => element(),
    body: { classList: { add() {}, remove() {} }, appendChild() {}, removeChild() {} },
    documentElement: { getAttribute() { return 'en'; } },
    activeElement: null,
  };
  const health = options.health || {
    body: { schema: 'fundamental_forensics.health/v1', status: 'current', clocks: {} },
    headers: {},
  };
  let healthGate;
  if (options.healthDelay) {
    healthGate = {};
    healthGate.promise = new Promise((resolve) => { healthGate.resolve = resolve; });
  }
  // Optional per-call response sequences: options.catalogResponses and
  // options.statementsResponses are arrays whose elements are { status } (an
  // HTTP error answer) or { catalog } / { statements } (a payload answer);
  // the last element repeats once the sequence is exhausted. Absent — the
  // default — the single-answer options below answer exactly as before.
  // options.statementsGate ({ promise, resolve }) holds every statements
  // answer back until it is resolved by hand, so a prime can be left open.
  function sequenceStep(sequence, needle) {
    if (!sequence) return null;
    const seen = fetchCalls.filter((call) => call.url.indexOf(needle) >= 0).length;
    return sequence[Math.min(seen - 1, sequence.length - 1)];
  }

  function errorResponse(status) {
    return Promise.resolve({
      ok: false,
      status,
      headers: { get: () => '' },
      text: () => Promise.resolve('{"detail":"unavailable"}'),
    });
  }

  function envelopeResponse(payload) {
    const packed = envelope(payload);
    return Promise.resolve({
      ok: true,
      headers: { get: (name) => (name === 'X-FIF-Response-SHA256' ? packed.sha256 : '') },
      arrayBuffer: () => Promise.resolve(packed.body.buffer.slice(
        packed.body.byteOffset, packed.body.byteOffset + packed.body.byteLength
      )),
    });
  }

  function responseFor(url, init) {
    const text = init && init.body ? String(init.body) : '';
    fetchCalls.push({ url: String(url), body: text, method: init && init.method });
    if (String(url).indexOf('/api/forensics/health') >= 0) {
      const answer = () => Promise.resolve({
        ok: true,
        headers: { get: (name) => (health.headers && health.headers[name]) || '' },
        json: () => Promise.resolve(JSON.parse(JSON.stringify(health.body))),
      });
      return healthGate ? healthGate.promise.then(answer) : answer();
    }
    if (String(url).indexOf('/api/forensics/v1/financial/catalog') >= 0) {
      const step = sequenceStep(options.catalogResponses, '/api/forensics/v1/financial/catalog');
      if (step) return step.status ? errorResponse(step.status) : envelopeResponse(step.catalog || { entity: {}, filings: null });
      if (options.catalogStatus) {
        return Promise.resolve({
          ok: false,
          status: options.catalogStatus,
          headers: { get: () => '' },
          text: () => Promise.resolve('{"detail":"unavailable"}'),
        });
      }
      const packed = envelope(options.catalog || { entity: {}, filings: null });
      return Promise.resolve({
        ok: true,
        headers: { get: (name) => (name === 'X-FIF-Response-SHA256' ? packed.sha256 : '') },
        arrayBuffer: () => Promise.resolve(packed.body.buffer.slice(
          packed.body.byteOffset, packed.body.byteOffset + packed.body.byteLength
        )),
      });
    }
    if (String(url).indexOf('/api/forensics/v1/financial/statements') >= 0) {
      const step = sequenceStep(options.statementsResponses, '/api/forensics/v1/financial/statements');
      if (step && step.status) return errorResponse(step.status);
      if (step || options.statementsGate) {
        const answer = () => envelopeResponse((step && (step.statements || statementsPayload()))
          || options.statements || statementsPayload());
        return options.statementsGate ? options.statementsGate.promise.then(answer) : answer();
      }
      const packed = envelope(options.statements || statementsPayload());
      return Promise.resolve({
        ok: true,
        headers: { get: (name) => (name === 'X-FIF-Response-SHA256' ? packed.sha256 : '') },
        arrayBuffer: () => Promise.resolve(packed.body.buffer.slice(
          packed.body.byteOffset, packed.body.byteOffset + packed.body.byteLength
        )),
      });
    }
    if (options.queryStatus) {
      const status = options.queryStatus;
      const raw = options.queryBody || '{"detail":"duplicate period"}';
      return Promise.resolve({
        ok: false,
        status,
        headers: { get: () => '' },
        text: () => Promise.resolve(raw),
      });
    }
    const answer = () => ({
      ok: true,
      headers: { get: (name) => (name === 'X-FIF-Response-SHA256' ? QUERY_ENVELOPE.sha256 : '') },
      arrayBuffer: () => Promise.resolve(QUERY_ENVELOPE.body.buffer.slice(
        QUERY_ENVELOPE.body.byteOffset, QUERY_ENVELOPE.body.byteOffset + QUERY_ENVELOPE.body.byteLength
      )),
    });
    // PF r2: deterministically hold the previous compare chain while a new
    // earlier-day selection rejects without POST, then release the old reply.
    return options.finGate ? options.finGate.promise.then(answer) : Promise.resolve(answer());
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
    // The page calls bare fetch/crypto/subtle — contextifying the sandbox
    // object makes these the page's globals, exactly like a browser window.
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
  return { api, nodes, windowListeners, pushes, location, storage, fetchCalls, healthGate };
}

async function settle() {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1));
  }
}

function financialPosts(drive) {
  return drive.fetchCalls.filter((call) => call.url.indexOf('/api/forensics/v1/financial/') >= 0);
}

// PF r1 (R1/R2): the compare chain now waits for the SELECTED issuer's
// accepted health answer (state.healthAnswer) rather than any state.health.
// Direct-injection tests seed the answer the loadHealth they skip would have
// recorded: the selected issuer, the harness-start seq, ok, and the pointer
// header value that matches the injected mode/generation world.
function seedAcceptedHealth(pointer) {
  return { entity_id: AAPL_ENTITY, seq: 0, ok: true, pointer: pointer || '' };
}

// ── PF-1 ────────────────────────────────────────────────────────────────────

test('PF-1: shared periods across statements collapse to one column, first label, first order', async () => {
  const drive = harness();
  drive.api.setTab('statements', false);
  await settle();
  const columns = Array.from(drive.api.state.statementColumns);
  assert.equal(columns.length, 4, 'two statements x three columns dedup to four periods');
  assert.deepEqual(
    columns.map((column) => [column.start, column.end]),
    [
      ['2024-09-29', '2025-09-27'],
      ['2023-10-01', '2024-09-28'],
      ['2022-10-01', '2023-09-30'],
      ['2021-10-01', '2022-09-28'],
    ],
    'first-seen order with duplicates removed'
  );
  assert.equal(columns[1].label, 'FY2024', 'the FIRST column keeps its own label');
  assert.equal(columns[2].label, 'FY2023', 'a later statement cannot relabel a seen period');
});

test('PF-1: the revisions request body carries no repeated period', async () => {
  const drive = harness();
  drive.api.state.health = { status: 'current', clocks: { broad_source_at: '2026-10-11T23:59:59Z' } };
  drive.api.state.healthAnswer = seedAcceptedHealth('');
  drive.api.setTab('statements', false);
  await settle();
  drive.api.setTab('compare', false);
  await settle();
  const revisions = financialPosts(drive).filter((call) => call.url.indexOf('/financial/revisions') >= 0);
  assert.ok(revisions.length >= 1, 'the revisions leg posted');
  const body = JSON.parse(revisions[revisions.length - 1].body);
  const keys = body.periods.map((period) => period.kind + '|' + period.start + '|' + period.end);
  assert.equal(new Set(keys).size, keys.length, 'no period key repeats on the wire');
  assert.equal(keys.length, 4);
});

// ── PF-2 ────────────────────────────────────────────────────────────────────

test('PF-2: financialPost attaches the parsed JSON detail to the thrown error', async () => {
  const drive = harness({ queryStatus: 400, queryBody: '{"detail":"duplicate period"}' });
  drive.api.state.health = { status: 'current', clocks: { broad_source_at: '2026-10-11T23:59:59Z' } };
  drive.api.state.healthAnswer = seedAcceptedHealth('');
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(drive.api.state.financial.phase, 'error');
  assert.equal(drive.api.state.financial.errorStatus, 400);
  assert.equal(drive.api.state.financial.errorDetail, 'duplicate period');
});

test('PF-2: a non-JSON error body leaves detail empty and parsing never throws twice', async () => {
  const drive = harness({ queryStatus: 502, queryBody: 'gateway teapot' });
  drive.api.state.health = { status: 'current', clocks: { broad_source_at: '2026-10-11T23:59:59Z' } };
  drive.api.state.healthAnswer = seedAcceptedHealth('');
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(drive.api.state.financial.phase, 'error');
  assert.equal(drive.api.state.financial.errorStatus, 502);
  assert.equal(drive.api.state.financial.errorDetail, '');
});

test('PF-2: only unknown entity keeps the identity copy', () => {
  const drive = harness();
  drive.api.state.financial = { phase: 'error', errorStatus: 400, errorDetail: 'unknown entity' };
  drive.api.renderRevisions();
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Issuer identity unavailable/);
  assert.match(html, /发行人标识不可用/);
});

test('PF-2: any other 400 shows the could-not-evaluate copy, never a raw detail', () => {
  const drive = harness();
  drive.api.state.financial = { phase: 'error', errorStatus: 400, errorDetail: 'duplicate period' };
  drive.api.renderRevisions();
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /This view could not be evaluated/);
  assert.match(html, /该公司与日期的请求被拒绝，因此不显示任何内容。我们不做猜测。/);
  assert.doesNotMatch(html, /duplicate period/);
  assert.doesNotMatch(html, /Issuer identity unavailable/);
  assert.doesNotMatch(html, /400/);
});

test('PF-2: the no-clocks phase shows the no-recorded-cutoff copy', () => {
  const drive = harness();
  drive.api.state.financial = { phase: 'no-clocks' };
  drive.api.renderRevisions();
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /No recorded cutoff yet/);
  assert.match(html, /尚无记录截止时点/);
  assert.match(html, /请在下次构建后再查看。/);
  assert.doesNotMatch(html, /Issuer identity unavailable/);
});

test('PF-2: a genuine 503 keeps today’s copy and the Retry button', () => {
  const drive = harness();
  drive.api.state.financial = { phase: 'error', errorStatus: 503, errorDetail: 'financial query temporarily unavailable' };
  drive.api.renderRevisions();
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Revisions temporarily unavailable/);
  assert.match(html, /data-financial-retry="1"/);
  assert.doesNotMatch(html, /financial query temporarily unavailable/);
});

// ── PF-3 (page) ─────────────────────────────────────────────────────────────

function healthWith(clocks, generation, mode) {
  const headers = {};
  if (mode) headers['X-FIF-Financial-Dataset-Mode'] = mode;
  if (generation) {
    headers['X-FIF-Dataset-Generation-Id'] = generation.id;
    headers['X-FIF-Dataset-Admitted-At'] = generation.admitted_at;
  }
  return {
    body: { schema: 'fundamental_forensics.health/v1', status: 'current', clocks },
    headers,
  };
}

test('PF-3: Latest recorded_at is the latest of the three present values — generation wins', () => {
  const drive = harness();
  drive.api.state.health = healthWith(
    { composed_state_at: '2026-10-10T00:00:00Z', broad_source_at: '2026-10-11T00:00:00Z' },
    { id: 'ffprods_gen2', admitted_at: '2026-10-12T01:00:00.000000Z', entity_id: AAPL_ENTITY },
    'production'
  ).body;
  drive.api.state.health.generation = { id: 'ffprods_gen2', admitted_at: '2026-10-12T01:00:00.000000Z', entity_id: AAPL_ENTITY };
  drive.api.state.datasetMode = 'production';
  drive.api.state.asOfDate = '';
  const clocks = drive.api.policyClocks();
  assert.equal(clocks.recorded_at, '2026-10-12T01:00:00.000000Z', 'the generation admission is the latest instant');
  assert.equal(clocks.source_snapshot_at, '2026-10-11T00:00:00Z', 'source_snapshot_at stays broad_source_at');
});

test('PF-3: composed_state_at wins when it is the latest', () => {
  const drive = harness();
  drive.api.state.health = {
    clocks: { composed_state_at: '2026-10-13T00:00:00Z', broad_source_at: '2026-10-11T00:00:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-12T01:00:00Z', entity_id: AAPL_ENTITY },
  };
  drive.api.state.datasetMode = 'production';
  const clocks = drive.api.policyClocks();
  assert.equal(clocks.recorded_at, '2026-10-13T00:00:00Z');
  assert.equal(clocks.source_snapshot_at, '2026-10-11T00:00:00Z');
});

test('PF-3: broad_source_at wins when it is the latest', () => {
  const drive = harness();
  drive.api.state.health = {
    clocks: { composed_state_at: '2026-10-10T00:00:00Z', broad_source_at: '2026-10-14T00:00:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-12T01:00:00Z', entity_id: AAPL_ENTITY },
  };
  drive.api.state.datasetMode = 'production';
  const clocks = drive.api.policyClocks();
  assert.equal(clocks.recorded_at, '2026-10-14T00:00:00Z');
  assert.equal(clocks.source_snapshot_at, '2026-10-14T00:00:00Z');
});

test('PF-3: with no value present the cutoff is empty and the honest no-clocks copy shows', () => {
  const drive = harness();
  drive.api.state.health = { clocks: {} };
  drive.api.state.datasetMode = 'production';
  const clocks = drive.api.policyClocks();
  assert.equal(clocks.recorded_at, '');
  assert.equal(clocks.source_snapshot_at, '');
  drive.api.state.financial = { phase: 'no-clocks' };
  drive.api.renderRevisions();
  assert.match(drive.nodes['ff-revisions-table'].innerHTML, /No recorded cutoff yet/);
});

test('PF-3: the generation candidate counts only in production mode and only for the selected issuer', () => {
  const laterGeneration = { id: 'ffprods_gen2', admitted_at: '2026-10-15T00:00:00Z', entity_id: MSFT_ENTITY };
  const golden = harness();
  golden.api.state.health = {
    clocks: { composed_state_at: '2026-10-10T00:00:00Z', broad_source_at: '2026-10-10T00:00:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-15T00:00:00Z', entity_id: AAPL_ENTITY },
  };
  golden.api.state.datasetMode = 'golden';
  assert.equal(golden.api.policyClocks().recorded_at, '2026-10-10T00:00:00Z', 'golden mode never uses the generation');

  const foreign = harness();
  foreign.api.state.health = {
    clocks: { composed_state_at: '2026-10-10T00:00:00Z', broad_source_at: '2026-10-10T00:00:00Z' },
    generation: laterGeneration,
  };
  foreign.api.state.datasetMode = 'production';
  assert.equal(
    foreign.api.policyClocks().recorded_at,
    '2026-10-10T00:00:00Z',
    'a generation for another issuer never becomes the selected desk’s cutoff'
  );

  const missingMode = harness();
  missingMode.api.state.health = {
    clocks: { composed_state_at: '2026-10-10T00:00:00Z', broad_source_at: '2026-10-10T00:00:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-15T00:00:00Z', entity_id: AAPL_ENTITY },
  };
  assert.equal(missingMode.api.policyClocks().recorded_at, '2026-10-10T00:00:00Z', 'a missing mode header keeps today’s behaviour');
});

test('PF-3: source_snapshot_at falls back to recorded_at when broad_source_at is absent', () => {
  const drive = harness();
  drive.api.state.health = { clocks: { composed_state_at: '2026-10-13T00:00:00Z' } };
  drive.api.state.datasetMode = 'production';
  const clocks = drive.api.policyClocks();
  assert.equal(clocks.recorded_at, '2026-10-13T00:00:00Z');
  assert.equal(clocks.source_snapshot_at, '2026-10-13T00:00:00Z');
});

test('PF-3: loadHealth sends entity_id for the selected company and re-fetches on change', async () => {
  const drive = harness();
  await drive.api.loadHealth();
  const first = drive.fetchCalls.filter((call) => call.url.indexOf('/api/forensics/health') >= 0);
  assert.equal(first.length, 1);
  assert.match(first[0].url, /[?]entity_id=ISS%3AUS-XNAS-AAPL$/);

  drive.api.state.symbol = 'MSFT';
  await drive.api.loadHealth();
  const second = drive.fetchCalls.filter((call) => call.url.indexOf('/api/forensics/health') >= 0);
  assert.equal(second.length, 2);
  assert.match(second[1].url, /[?]entity_id=ISS%3AUS-XNAS-MSFT$/);
});

test('PF-3: a health response for a deselected company is dropped', async () => {
  const drive = harness({
    healthDelay: true,
    health: healthWith(
      { broad_source_at: '2026-10-11T00:00:00Z' },
      { id: 'ffprods_msft', admitted_at: '2026-10-12T01:00:00Z' },
      'production'
    ),
  });
  const pending = drive.api.loadHealth();
  // The user switches companies BEFORE the health answer lands.
  drive.api.state.symbol = 'MSFT';
  drive.healthGate.resolve();
  await pending;
  await settle();
  assert.equal(drive.api.state.health, undefined, 'the stale AAPL answer never became the desk health');
  assert.equal(drive.api.state.datasetMode, '', 'no mode header was recorded either');
});

test('PF-3: a health response for the still-selected company is applied', async () => {
  const drive = harness({
    health: healthWith(
      { broad_source_at: '2026-10-11T00:00:00Z' },
      { id: 'ffprods_aapl', admitted_at: '2026-10-12T01:00:00Z' },
      'production'
    ),
  });
  await drive.api.loadHealth();
  assert.ok(drive.api.state.health, 'the answer applies');
  assert.equal(drive.api.state.datasetMode, 'production');
  assert.equal(drive.api.state.health.generation.entity_id, AAPL_ENTITY, 'the generation is stored with its entity');
});

test('PF-3: reResolveSavedView no longer returns clocks when the helper has a value', async () => {
  const drive = harness({
    health: healthWith(
      { broad_source_at: '2026-10-11T23:59:59Z' },
      { id: 'ffprods_gen9', admitted_at: '2026-10-12T01:00:00Z' },
      'production'
    ),
  });
  const container = JSON.parse(readFileSync(new URL('saved_pinned.json', FIXTURE_DIR), 'utf8'));
  drive.storage.setItem(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  const restore = drive.api.restoreSavedView(container.saved_views[0].id);
  assert.equal(restore.ok, true, restore.reason || 'restore refused');
  await settle();
  assert.equal(drive.api.state.datasetMode, 'production');
  assert.equal(drive.api.state.health.generation.entity_id, AAPL_ENTITY);
  const result = drive.api.reResolveSavedView();
  assert.equal(result.ok, true, 'a broad_source_at + matching generation cutoff re-resolves');
  const view = JSON.parse(drive.storage.get(STORE_KEY));
  const resolved = view.saved_views.find((row) => row.id === container.saved_views[0].id);
  assert.equal(resolved.request.policy.recorded_at, '2026-10-12T01:00:00Z', 'recorded_at is the latest instant');
  assert.equal(resolved.request.policy.source_snapshot_at, '2026-10-11T23:59:59Z');
  assert.equal(resolved.pinned, false);
});

test('PF-3: savedGenerationStale ignores a generation belonging to another issuer', async () => {
  const drive = harness();
  const container = JSON.parse(readFileSync(new URL('saved_pinned.json', FIXTURE_DIR), 'utf8'));
  drive.storage.setItem(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  drive.api.restoreSavedView(container.saved_views[0].id);
  await settle();
  drive.api.state.health = {
    clocks: {},
    generation: { id: 'ffprods_other', admitted_at: '2026-10-12T01:00:00Z', entity_id: MSFT_ENTITY },
  };
  assert.equal(drive.api.savedGenerationStale(), null, 'an MSFT generation never marks an AAPL view stale');
});

// ── PF-4 ────────────────────────────────────────────────────────────────────

test('PF-4: a picked day before the admitted day sends NO query and shows the earlier-dates copy', async () => {
  const drive = harness({
    health: healthWith(
      { broad_source_at: '2026-10-13T02:05:00Z' },
      { id: 'ffprods_gen2', admitted_at: '2026-10-13T02:00:00.000000Z' },
      'production'
    ),
  });
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: { broad_source_at: '2026-10-13T02:05:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-13T02:00:00.000000Z', entity_id: AAPL_ENTITY },
  };
  drive.api.state.healthAnswer = seedAcceptedHealth('admitted');
  drive.api.state.asOfDate = '2026-10-12';
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0, 'no financial query is sent for a pre-admission day');
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Earlier dates not available/);
  assert.match(html, /This company&#39;s filing records were last published on 2026-10-13\./);
  assert.match(html, /该公司的申报记录最近一次发布于2026-10-13。/);
  assert.match(html, /或使用“最新”。/);
});

test('PF-4: the earlier-dates fact precedes the period check — a state without period starts must not mask it', async () => {
  const drive = harness();
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: { broad_source_at: '2026-10-13T02:05:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-13T02:00:00.000000Z', entity_id: AAPL_ENTITY },
  };
  drive.api.state.healthAnswer = seedAcceptedHealth('admitted');
  // The state projection genuinely carries no period start (absent_in_projection).
  drive.api.state.payload.companies.AAPL.periods = [{ fiscal_year: 2024, start: null, end: '2024-09-28' }];
  drive.api.state.asOfDate = '2026-10-12';
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0, 'still no query');
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Earlier dates not available/, 'the day fact wins over the period fact');
  assert.doesNotMatch(html, /Period start unavailable/);
});

test('PF-4: the admitted day itself sends the query', async () => {
  const drive = harness();
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: { broad_source_at: '2026-10-13T02:05:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-13T02:00:00.000000Z', entity_id: AAPL_ENTITY },
  };
  drive.api.state.healthAnswer = seedAcceptedHealth('admitted');
  drive.api.state.asOfDate = '2026-10-13';
  drive.api.setTab('compare', false);
  await settle();
  assert.ok(financialPosts(drive).length >= 4, 'the full compare chain fires (3 query legs + revisions)');
  const bodies = financialPosts(drive).map((call) => JSON.parse(call.body));
  for (const body of bodies) {
    assert.equal(body.policy.recorded_at, '2026-10-13T23:59:59Z', 'the picked day still drives both clocks');
  }
});

test('PF-4: the picker min is the admitted day in production and clears otherwise', async () => {
  const drive = harness({
    health: healthWith(
      { broad_source_at: '2026-10-13T02:05:00Z' },
      { id: 'ffprods_gen2', admitted_at: '2026-10-13T02:00:00.000000Z' },
      'production'
    ),
  });
  await drive.api.loadHealth();
  assert.equal(drive.nodes['ff-asof-input'].getAttribute('min'), '2026-10-13');

  // Company change: the generation no longer describes the selection.
  drive.api.state.symbol = 'MSFT';
  drive.api.setAsofControlsFromState();
  assert.equal(drive.nodes['ff-asof-input'].getAttribute('min'), null);

  // Golden mode never sets a min.
  const golden = harness({
    health: healthWith({ broad_source_at: '2026-10-13T02:05:00Z' }, null, 'golden'),
  });
  await golden.api.loadHealth();
  assert.equal(golden.nodes['ff-asof-input'].getAttribute('min'), null);
});

test('PF-4: production with pointer none sends NO query and shows the no-records copy', async () => {
  const drive = harness();
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = { status: 'current', clocks: { broad_source_at: '2026-10-13T02:05:00Z' } };
  // PF r1 (R2): the server's names-only pointer header now carries this fact;
  // a bare missing generation in production is the 503 case instead (pinned
  // in fundamental_forensics_pf_health.test.mjs).
  drive.api.state.healthAnswer = seedAcceptedHealth('none');
  drive.api.state.asOfDate = '';
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(financialPosts(drive).length, 0, 'no financial query without a published generation');
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /No filing records published yet/);
  assert.match(html, /We have not published filing records for this company yet, so no vintage is shown\./);
  assert.match(html, /尚未发布申报记录/);
  assert.match(html, /我们尚未发布该公司的申报记录，因此不显示任何版本。/);
});

test('PF-4: golden mode and a missing mode header keep today’s behaviour', async () => {
  const golden = harness();
  golden.api.state.datasetMode = 'golden';
  golden.api.state.health = { status: 'current', clocks: { broad_source_at: '2026-10-11T23:59:59Z' } };
  golden.api.state.healthAnswer = seedAcceptedHealth('');
  golden.api.state.asOfDate = '2026-01-15';
  golden.api.setTab('compare', false);
  await settle();
  assert.ok(financialPosts(golden).length >= 4, 'golden still queries on any picked day');

  const missingMode = harness();
  missingMode.api.state.health = {
    status: 'current',
    clocks: { broad_source_at: '2026-10-11T23:59:59Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2099-01-01T00:00:00Z', entity_id: AAPL_ENTITY },
  };
  missingMode.api.state.healthAnswer = seedAcceptedHealth('');
  missingMode.api.state.asOfDate = '2026-01-15';
  missingMode.api.setTab('compare', false);
  await settle();
  assert.ok(financialPosts(missingMode).length >= 4, 'a missing mode header keeps today’s query behaviour');
});


// ── PF round-2 independent review regressions ─────────────────────────────

test('PF r2 M1: stale in-flight Latest answers cannot overwrite a later earlier-day refusal', async () => {
  let release;
  const finGate = { promise: new Promise((resolve) => { release = resolve; }) };
  const drive = harness({ finGate });
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: { broad_source_at: '2026-10-13T02:05:00Z', composed_state_at: '2026-10-13T02:05:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-13T02:00:00.000000Z', entity_id: AAPL_ENTITY },
  };
  drive.api.state.healthAnswer = seedAcceptedHealth('admitted');
  drive.api.setTab('compare', false);
  await settle();
  const pending = financialPosts(drive).length;
  assert.ok(pending >= 4, 'the prior Latest chain was actually dispatched and held');
  assert.equal(drive.api.state.financial.phase, 'loading');
  const oldToken = drive.api.state.financialToken;
  drive.api.state.asOfDate = '2026-10-12';
  drive.api.ensureFinancialData();
  assert.ok(drive.api.state.financialToken > oldToken, 'the early-return path invalidates old replies');
  assert.equal(financialPosts(drive).length, pending, 'earlier-day refuses without a new POST');
  assert.equal(drive.api.state.financial.phase, 'earlier');
  release();
  await settle();
  assert.equal(drive.api.state.financial.phase, 'earlier', 'old successful answers cannot overwrite the refusal');
  assert.match(drive.nodes['ff-revisions-table'].innerHTML, /Earlier dates not available/);
});

test('PF r2 m2: missing generation or target issuer ID can never match through empty strings', () => {
  const drive = harness();
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: {}, generation: { id: 'ffprods_other', admitted_at: '2026-10-13T02:00:00Z' },
  };
  assert.equal(drive.api.selectedGeneration(), null, 'no generation issuer ID is not this company');
  drive.api.state.payload.companies.AAPL.entity_id = '';
  assert.equal(drive.api.selectedGeneration(), null, 'two empty issuer IDs do not match');
  drive.api.state.health.generation.entity_id = AAPL_ENTITY;
  assert.equal(drive.api.selectedGeneration(), null, 'generation ID without target ID does not match');
});

test('PF r2 m3: health outage is described as data unavailable, not revisions unavailable', () => {
  const drive = harness();
  drive.api.state.financial = { phase: 'error', healthRetry: true };
  drive.api.renderRevisions();
  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.match(html, /Data temporarily unavailable/);
  assert.match(html, /数据暂不可用/);
  assert.match(html, /data-financial-retry="1"/);
  assert.doesNotMatch(html, /Revisions temporarily unavailable/);
  drive.api.state.financial = { phase: 'error', healthRetry: false, errorStatus: 503 };
  drive.api.renderRevisions();
  assert.match(drive.nodes['ff-revisions-table'].innerHTML, /Revisions temporarily unavailable/,
    'ordinary revisions outage retains the existing specific copy');
});

test('PF r2 n1: picker floor uses the UTC admission day, not raw offset date', () => {
  const drive = harness();
  drive.api.state.datasetMode = 'production';
  drive.api.state.health = {
    clocks: {}, generation: {
      id: 'ffprods_gen2',
      admitted_at: '2026-10-12T23:30:00-05:00',
      entity_id: AAPL_ENTITY,
    },
  };
  drive.api.setAsofControlsFromState();
  assert.equal(drive.nodes['ff-asof-input'].getAttribute('min'), '2026-10-13',
    'date-range floor agrees with UTC end-of-day admission checks');
  drive.api.state.health.generation.admitted_at = 'invalid';
  drive.api.setAsofControlsFromState();
  assert.equal(drive.nodes['ff-asof-input'].getAttribute('min'), null);
});

// ── Catalog, served filing and units (FIF a/b/e/f) ─────────────────────────
//
// Pins:
// - (e) in production the statements accession comes from the generation's
//   own catalog: the panel accession is kept only when the catalog lists it,
//   otherwise the latest listed periodic report (original ahead of its
//   amendment); no listed periodic report means no statements request.
//   Golden mode, a failed catalog, another issuer's catalog and a malformed
//   filings field all keep the panel accession.
// - (f) production periods without starts are primed once from that same
//   catalog-resolved statement tree; a failed prime settles into no-periods.
// - (a) the served filing is named beside the tree, in both languages.
// - (b) a statement cell's unit picks its display: shares are never dollars.

const PANEL_ACCESSION = '0000320193-25-000079';

function catalogPayload(entityId, filings) {
  return {
    schema: 'fundamental_forensics.financial_catalog_response/v1',
    entity: { entity_id: entityId, cik: '0000320193' },
    filings,
  };
}

function postsTo(drive, suffix) {
  return drive.fetchCalls.filter((call) => call.url.indexOf('/api/forensics/v1/financial/' + suffix) >= 0);
}

function statementAccessions(drive) {
  return postsTo(drive, 'statements').map((call) => JSON.parse(call.body).accession);
}

const LATER_FILINGS = [
  { form: '10-Q', accession: '0000320193-26-000006', period_of_report: '2025-12-27', filing_date: '2026-01-30' },
  { form: '10-Q/A', accession: '0000320193-26-000021', period_of_report: '2026-03-28', filing_date: '2026-06-15' },
  { form: '10-Q', accession: '0000320193-26-000020', period_of_report: '2026-03-28', filing_date: '2026-05-01' },
  { form: '8-K', accession: '0000320193-26-000030', period_of_report: '2026-06-01', filing_date: '2026-06-02' },
];

const ONLY_CURRENT_REPORT = [
  { form: '8-K', accession: '0000320193-26-000030', period_of_report: '2026-06-01', filing_date: '2026-06-02' },
];

function primeDrive(options) {
  const drive = harness(options);
  drive.api.state.payload.companies.AAPL.periods = [{ fiscal_year: 2024, start: null, end: '2024-09-28' }];
  drive.api.state.health = {
    clocks: { broad_source_at: '2026-10-13T02:05:00Z' },
    generation: { id: 'ffprods_gen2', admitted_at: '2026-10-13T02:00:00.000000Z', entity_id: AAPL_ENTITY },
  };
  drive.api.state.healthAnswer = seedAcceptedHealth('admitted');
  drive.api.state.asOfDate = '2026-10-13';
  return drive;
}

test('FIF e: production asks the catalog and opens the latest listed periodic report', async () => {
  const drive = harness({ catalog: catalogPayload(AAPL_ENTITY, LATER_FILINGS) });
  drive.api.state.datasetMode = 'production';
  drive.api.setTab('statements', false);
  await settle();
  const catalogPosts = postsTo(drive, 'catalog');
  assert.equal(catalogPosts.length, 1, 'one catalog request');
  assert.deepEqual(JSON.parse(catalogPosts[0].body), {
    schema: 'fundamental_forensics.financial_catalog_request/v1',
    entity_id: AAPL_ENTITY,
  });
  assert.deepEqual(statementAccessions(drive), ['0000320193-26-000020'],
    'the unlisted panel accession is replaced by the original 10-Q for the latest period');
  assert.equal(drive.api.state.statements.phase, 'ready');
});

test('FIF e: a panel accession the catalog lists is kept', async () => {
  const listed = [{ form: '10-K', accession: PANEL_ACCESSION, period_of_report: '2025-09-27', filing_date: '2025-10-31' }]
    .concat(LATER_FILINGS);
  const drive = harness({ catalog: catalogPayload(AAPL_ENTITY, listed) });
  drive.api.state.datasetMode = 'production';
  drive.api.setTab('statements', false);
  await settle();
  assert.equal(postsTo(drive, 'catalog').length, 1);
  assert.deepEqual(statementAccessions(drive), [PANEL_ACCESSION]);
});

test('FIF e: golden mode never asks the catalog and keeps the panel accession', async () => {
  const drive = harness({ catalog: catalogPayload(AAPL_ENTITY, LATER_FILINGS) });
  drive.api.state.datasetMode = 'golden';
  drive.api.setTab('statements', false);
  await settle();
  assert.equal(postsTo(drive, 'catalog').length, 0, 'no catalog request outside production');
  assert.deepEqual(statementAccessions(drive), [PANEL_ACCESSION]);
});

test('FIF e: a failed, foreign or malformed catalog keeps the panel accession', async () => {
  const cases = [
    { catalogStatus: 503 },
    { catalog: catalogPayload(MSFT_ENTITY, LATER_FILINGS) },
    { catalog: catalogPayload(AAPL_ENTITY, 'not-a-list') },
  ];
  for (const options of cases) {
    const drive = harness(options);
    drive.api.state.datasetMode = 'production';
    drive.api.setTab('statements', false);
    await settle();
    assert.equal(postsTo(drive, 'catalog').length, 1, 'the catalog was asked once');
    assert.deepEqual(statementAccessions(drive), [PANEL_ACCESSION], JSON.stringify(Object.keys(options)));
  }
});

test('FIF e: no listed periodic report means no statements request', async () => {
  const drive = harness({ catalog: catalogPayload(AAPL_ENTITY, ONLY_CURRENT_REPORT) });
  drive.api.state.datasetMode = 'production';
  drive.api.setTab('statements', false);
  await settle();
  assert.equal(postsTo(drive, 'catalog').length, 1);
  assert.equal(postsTo(drive, 'statements').length, 0, 'a current report is never opened as a statement tree');
  assert.equal(drive.api.state.statements.phase, 'unavailable');
});

test('FIF f: production periods without starts are primed from the catalog-resolved tree', async () => {
  const drive = primeDrive({ catalog: catalogPayload(AAPL_ENTITY, LATER_FILINGS) });
  drive.api.state.datasetMode = 'production';
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(postsTo(drive, 'catalog').length, 1, 'the prime asks the catalog once');
  assert.deepEqual(statementAccessions(drive), ['0000320193-26-000020']);
  assert.equal(drive.api.state.statementColumns.length, 4, 'the primed columns are de-duplicated');
  assert.notEqual(drive.api.state.financial.phase, 'no-periods');
  const revisions = postsTo(drive, 'revisions');
  assert.ok(revisions.length >= 1, 'the revisions leg posted');
  const body = JSON.parse(revisions[revisions.length - 1].body);
  assert.deepEqual(
    body.periods.map((period) => [period.start, period.end]),
    [
      ['2024-09-29', '2025-09-27'],
      ['2023-10-01', '2024-09-28'],
      ['2022-10-01', '2023-09-30'],
      ['2021-10-01', '2022-09-28'],
    ]
  );
});

test('FIF f: a prime with no listed periodic report settles into no-periods without a query', async () => {
  const drive = primeDrive({ catalog: catalogPayload(AAPL_ENTITY, ONLY_CURRENT_REPORT) });
  drive.api.state.datasetMode = 'production';
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(postsTo(drive, 'catalog').length, 1);
  assert.equal(postsTo(drive, 'statements').length, 0);
  assert.equal(postsTo(drive, 'query').length, 0, 'no query leg without periods');
  assert.equal(postsTo(drive, 'revisions').length, 0);
  assert.equal(drive.api.state.financial.phase, 'no-periods');
});

test('FIF f: golden periods without starts never prime', async () => {
  const drive = primeDrive({ catalog: catalogPayload(AAPL_ENTITY, LATER_FILINGS) });
  drive.api.state.datasetMode = 'golden';
  drive.api.state.health = { status: 'current', clocks: { broad_source_at: '2026-10-11T23:59:59Z' } };
  drive.api.state.healthAnswer = seedAcceptedHealth('');
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(postsTo(drive, 'catalog').length, 0);
  assert.equal(postsTo(drive, 'statements').length, 0);
  assert.equal(drive.api.state.financial.phase, 'no-periods');
});

function unitRow(label, value, unit) {
  return {
    as_reported_label: label,
    standardized_metric_id: '',
    cells: [{ value, unit, quality_state: 'available' }],
  };
}

function servedFilingStatements() {
  return {
    filing: {
      form: '10-Q',
      accession: '0000320193-26-000020',
      period_of_report: '2026-03-28',
      filing_date: '2026-05-01',
    },
    statements: [{
      title: 'CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS',
      statement_type: 'income_statement',
      columns: [{ label: 'Three months ended 2026-03-28', start: '2025-12-28', end: '2026-03-28' }],
      rows: [
        unitRow('Total net sales', '95400000000', 'USD'),
        unitRow('Shares used in computing earnings per share', '15200000000', 'shares'),
        unitRow('Shares outstanding', '15000000000', 'xbrli:shares'),
        unitRow('Diluted earnings per share', '1.65', 'USD/shares'),
        unitRow('Other income/(expense), net', '-1200000000', 'iso4217:USD'),
        unitRow('Foreign subsidiary revenue', '5000000', 'EUR'),
        unitRow('Effective tax rate', '0.47', 'pure'),
      ],
    }],
  };
}

test('FIF b: a statement cell unit picks its display, shares are never dollars', async () => {
  const drive = harness({ statements: servedFilingStatements() });
  drive.api.setTab('statements', false);
  await settle();
  assert.equal(drive.api.state.statements.phase, 'ready');
  const html = drive.nodes['ff-statements'].innerHTML;
  assert.match(html, /tnum">\$95\.4B</, 'USD is money');
  assert.match(html, /tnum">15\.2B</, 'a share count is a plain compact count');
  assert.doesNotMatch(html, /\$15\.2B/, 'a share count is never dollars');
  assert.match(html, /tnum">15B</, 'a prefixed share unit is still shares');
  assert.doesNotMatch(html, /\$15B/);
  assert.match(html, /tnum">\$1\.65</, 'USD per share keeps the money format');
  assert.match(html, /tnum">−\$1\.2B</, 'a prefixed negative USD keeps the money format and sign');
  assert.match(html, /tnum">5M EUR</, 'another currency is named, never shown as dollars');
  assert.match(html, /tnum">0\.47</, 'a pure ratio is a plain number');
});

test('FIF a: the served filing is named beside the tree in both languages', async () => {
  const drive = harness({ statements: servedFilingStatements() });
  drive.api.setTab('statements', false);
  await settle();
  const html = drive.nodes['ff-statements'].innerHTML;
  assert.ok(html.startsWith('<p class="ff-statement-notice">'), 'the caption leads the tree');
  assert.ok(html.includes(
    'As-reported filing shown: 10-Q · period ending 2026-03-28 · filed 2026-05-01 · accession 0000320193-26-000020'
  ));
  assert.ok(html.includes(
    '所示按披露原样的财报：10-Q · 报告期截至2026-03-28 · 提交于2026-05-01 · 文件编号 0000320193-26-000020'
  ));

  const bare = harness();
  bare.api.setTab('statements', false);
  await settle();
  assert.equal(bare.api.state.statements.phase, 'ready');
  assert.doesNotMatch(bare.nodes['ff-statements'].innerHTML, /ff-statement-notice/,
    'a payload without a filing names no filing');
});

// ── Catalog retry, prime reset guard, transition reports (review round 3) ───
//
// Pins:
// - a REJECTED catalog request (HTTP error / transport failure) is never
//   reused: the caller waiting on it still gets phase 'none' and the panel
//   accession, but the next open asks the catalog again. A foreign-entity or
//   malformed payload settles from the resolve branch and STAYS cached.
// - a prime request that was open across a statements reset (company
//   A → B → A) can no longer write the columns of the reset state.
// - the transition-period reports 10-KT and 10-QT are periodic reports, so a
//   catalog whose latest periodic filing is a transition report opens it.

test('FIF e: a rejected catalog answer is not reused — the next open asks again', async () => {
  const drive = harness({
    catalogResponses: [
      { status: 503 },
      { catalog: catalogPayload(AAPL_ENTITY, LATER_FILINGS) },
    ],
    statementsResponses: [{ status: 503 }, {}],
  });
  drive.api.state.datasetMode = 'production';
  drive.api.setTab('statements', false);
  await settle();
  assert.equal(drive.api.state.statements.phase, 'error', 'the failed statements request lands in error');
  assert.equal(postsTo(drive, 'catalog').length, 1);
  assert.deepEqual(statementAccessions(drive), [PANEL_ACCESSION],
    'the rejected catalog leaves the panel accession for that open');

  drive.api.setTab('statements', false);
  await settle();
  assert.equal(postsTo(drive, 'catalog').length, 2, 'the catalog is asked again after the rejected entry');
  assert.deepEqual(statementAccessions(drive), [PANEL_ACCESSION, '0000320193-26-000020'],
    'the second statements request opens the catalog-resolved accession');
  assert.equal(drive.api.state.statements.phase, 'ready');
});

test('FIF e: a foreign-entity catalog answer stays cached across a statements retry', async () => {
  const drive = harness({
    catalogResponses: [{ catalog: catalogPayload(MSFT_ENTITY, LATER_FILINGS) }],
    statementsResponses: [{ status: 503 }, {}],
  });
  drive.api.state.datasetMode = 'production';
  drive.api.setTab('statements', false);
  await settle();
  assert.equal(drive.api.state.statements.phase, 'error');
  drive.api.setTab('statements', false);
  await settle();
  assert.equal(postsTo(drive, 'catalog').length, 1, 'a resolved foreign answer is reused, not re-asked');
  assert.deepEqual(statementAccessions(drive), [PANEL_ACCESSION, PANEL_ACCESSION],
    'the panel accession stays in force');
  assert.equal(drive.api.state.statements.phase, 'ready');
});

test('FIF f: a prime open across a statements reset never writes the columns', async () => {
  const gate = {};
  gate.promise = new Promise((resolve) => { gate.resolve = resolve; });
  const drive = primeDrive({
    catalog: catalogPayload(AAPL_ENTITY, LATER_FILINGS),
    statementsGate: gate,
  });
  drive.api.state.datasetMode = 'production';
  drive.api.setTab('compare', false);
  await settle();
  assert.equal(postsTo(drive, 'statements').length, 1, 'the prime request is open, held by the gate');

  // The page resets the statements state (the company switch A → B → A resets
  // exactly this way) while the old prime is still open, then the old answer
  // lands for the still-selected original company.
  drive.api.resetStatementsState();
  gate.resolve();
  await settle();
  assert.equal(postsTo(drive, 'statements').length, 1, 'no second statements request was needed');
  assert.equal(drive.api.state.statementColumns.length, 0,
    'the stale prime cannot write columns across a reset');
});

test('FIF e: a catalog whose latest periodic filing is a transition report opens it', async () => {
  for (const form of ['10-KT', '10-QT']) {
    const filings = [
      { form: '10-Q', accession: '0000320193-26-000006', period_of_report: '2025-12-27', filing_date: '2026-01-30' },
      { form, accession: '0000320193-26-000099', period_of_report: '2026-03-28', filing_date: '2026-05-01' },
    ];
    const drive = harness({ catalog: catalogPayload(AAPL_ENTITY, filings) });
    drive.api.state.datasetMode = 'production';
    drive.api.setTab('statements', false);
    await settle();
    assert.equal(drive.api.state.statements.phase, 'ready', form);
    assert.deepEqual(statementAccessions(drive), ['0000320193-26-000099'],
      form + ' is a periodic report and the latest period wins');
  }
});

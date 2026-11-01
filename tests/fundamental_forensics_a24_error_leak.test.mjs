// A24 — page error states leak no locked content while an authorized source
// trace still resolves (Z0 closure-matrix row A24).
//
// One page context whose fetch stub is programmable per URL drives the desk's
// own failure branches — bundle fetch rejection (templates/fundamental_
// forensics.js loadData catch :1009), bundle 503 (:967-973 -> showLoadError
// :925 -> GATE_COPY.unavailable :839), health fetch rejection (loadHealth
// catch :1286 -> applyHealth unavailable :1317), compare-chain network and
// 500 failures (financialPost :2029, ensureFinancialData catch :2240, export
// runExport catch :3413), and attested-history rejections (historyRequest
// :4404 with the catches at :4495 and :4527). For each state the suite pins:
//   * the page's own error copy renders (gate 503/Retry copy, freshness
//     'Unavailable', 'Revisions temporarily unavailable' + Retry,
//     'Export unavailable', 'Run record temporarily unavailable' + Retry);
//   * the authorized node's text and its SEC source href still resolve — the
//     evidence drawer (renderEvidence :4988, receipt href :5010-5016) and the
//     trace panel (renderTrace :3875, receipt href :3910) are the surfaces the
//     failure branches leave standing;
//   * LOCKED-SENTINEL-7f3a — seeded into every value field of the withheld
//     shapes (refused statement identity, withheld statement cell, 'missing'
//     query node with a private receipt digest, javascript:-scheme receipt
//     url, and the 5xx response bodies themselves) — appears in no rendered
//     node and in no fetched URL (the S7 census).
// Only the page at BASE runs here; no production file is edited.
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const PAGE_SOURCE = readFileSync(new URL('../templates/fundamental_forensics.js', import.meta.url), 'utf8');

const SENTINEL = 'LOCKED-SENTINEL-7f3a';
const LOCKED_RECEIPT_ID = 'rawfact_' + SENTINEL;
const ENTITY_ID = 'ISS:US-XNAS-AAPL';
const AUTH_URL = 'https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm';
// A private-origin url safeUrl() refuses to link (templates :528-536): the
// bundle-native withheld shape — the locked bytes live only in the url field.
const LOCKED_URL = 'javascript:' + SENTINEL;

function hex64(seed) {
  return createHash('sha256').update(seed).digest('hex');
}

const AUTH_OCCURRENCE = 'rawfact_' + hex64('a24-authorized-occurrence');
const AUTH_ROOT_CELL = 'metric_cell_' + hex64('a24-authorized-root');
const AUTH_SNAPSHOT = 'ffqsv2_' + hex64('a24-authorized-snapshot');
const AUTH_ACCESSION = '0000320193-25-000079';

// ── fixtures ────────────────────────────────────────────────────────────────

// The bundle carries BOTH nodes: an authorized finding whose evidence receipt
// resolves through safeUrl(), and a locked receipt whose url never resolves.
function authorizedFinding() {
  return {
    id: 'FIND-AUTH-01',
    topic: 'revenue',
    detector: 'revenue_vs_growth',
    priority: 'high',
    title: 'Authorized revenue signal',
    summary_en: 'Authorized finding summary text',
    values: [{ key: 'revenue', label: 'Revenue', current: '416161000000', format: 'currency' }],
    evidence: [
      { url: AUTH_URL, label: 'FY2024 Form 10-K', basis: 'Form 10-K', date: '2025-02-03' },
      { url: LOCKED_URL, label: 'Locked private receipt', basis: 'Private ledger', date: '2025-02-03' },
    ],
    limitations_en: [],
    limitations_zh: []
  };
}

function bundlePayload() {
  return {
    companies: {
      AAPL: {
        symbol: 'AAPL',
        name: 'Apple Inc.',
        entity_id: ENTITY_ID,
        cik: '0000320193',
        sector: 'Information Technology',
        latest_filed: '2025-02-03',
        latest_period: 'FY2024',
        periods: [{ fiscal_year: 2024, start: '2023-10-01', end: '2024-09-28', filed: '2024-11-01' }],
        findings: [authorizedFinding()],
        coverage: {},
        disclosure_bundle: {
          tracks: [{
            status: 'ready',
            comparison: { note: 'fixture' },
            current_filing: { accession: AUTH_ACCESSION }
          }]
        }
      }
    },
    default_symbol: 'AAPL',
    ranked_findings: [],
    generated_at: '2026-10-13T02:05:00Z',
    source: {
      companyfacts_url_pattern: 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik10}',
      label: 'SEC Company Facts',
      basis: 'SEC EDGAR'
    }
  };
}

// The statements store: an authorized statement whose cells carry a resolvable
// source_receipt, a refused statement whose identity fields are locked bytes
// (rendered only as the fixed withheld heading + copy, templates :2557-2561),
// and a withheld cell (quality_state !== 'available', templates :2517-2525)
// whose value/unit/receipt ids are locked bytes.
function mixedStatements() {
  return {
    phase: 'ready',
    statements: [
      {
        statement_type: 'income_statement',
        title: 'CONSOLIDATED STATEMENTS OF OPERATIONS',
        columns: [{ label: 'FY2024', start: '2023-10-01', end: '2024-09-28' }],
        rows: [{
          as_reported_label: 'Total net sales',
          standardized_metric_id: 'revenue',
          cells: [{
            quality_state: 'available',
            value: '416161000000',
            unit: 'USD',
            source_receipt: {
              occurrence_id: AUTH_OCCURRENCE,
              root_cell_id: AUTH_ROOT_CELL,
              snapshot_id: AUTH_SNAPSHOT,
              accession: AUTH_ACCESSION,
              source_span: [12, 48]
            }
          }]
        }]
      },
      {
        statement_type: 'balance_sheet',
        role_uri: 'http://filer.example/role/' + SENTINEL,
        title: 'RAW ' + SENTINEL,
        columns: [],
        rows: [],
        row_count: 0,
        refusal: { code: 'displayed_columns_absent', message: SENTINEL }
      },
      {
        statement_type: 'cash_flow',
        title: 'CONSOLIDATED STATEMENTS OF CASH FLOWS',
        columns: [{ label: 'FY2024', start: '2023-10-01', end: '2024-09-28' }],
        rows: [{
          as_reported_label: 'Cash generated by operating activities',
          standardized_metric_id: 'cfo',
          cells: [{
            quality_state: 'withheld',
            value: SENTINEL,
            unit: SENTINEL,
            source_receipt: {
              occurrence_id: LOCKED_RECEIPT_ID,
              root_cell_id: SENTINEL,
              snapshot_id: SENTINEL,
              accession: SENTINEL,
              source_span: [1, 9]
            }
          }]
        }]
      }
    ]
  };
}

function authorizedQueryNode() {
  return {
    metric_id: 'revenue',
    value: '416161000000',
    unit: 'USD',
    display_excerpt: 'Total net sales … 416,161',
    provenance: {
      accession: AUTH_ACCESSION,
      selected_raw_fact: { occurrence_id: AUTH_OCCURRENCE, source_span: [12, 48] }
    },
    snapshot_id: AUTH_SNAPSHOT,
    cell_id: AUTH_ROOT_CELL
  };
}

// The locked query node: state 'missing' renders the absence copy only
// (templates :2279); the sentinel rides every value field plus the
// x-fif-receipt-sha256-style digest field the page reads elsewhere
// (companyfacts_response_sha256, templates :4346).
function lockedQueryNode() {
  return {
    metric_id: 'gross_profit',
    state: 'missing',
    value: SENTINEL,
    unit: SENTINEL,
    period_label: SENTINEL,
    display_excerpt: SENTINEL,
    provenance: {
      accession: SENTINEL,
      selected_raw_fact: { occurrence_id: LOCKED_RECEIPT_ID, source_span: [1, 9] }
    },
    snapshot_id: SENTINEL,
    cell_id: SENTINEL,
    companyfacts_response_sha256: SENTINEL
  };
}

// A /latest attested-history answer that passes checkedLatestReceipt()
// (templates :4180-4195) and matches the selected issuer's CIK.
function latestReceiptPayload() {
  return {
    snapshot_id: 'ffqsv2_' + hex64('a24-latest-snapshot'),
    base_snapshot_id: 'ffqs_' + hex64('a24-base-snapshot'),
    query_hash: hex64('a24-query-hash'),
    published_at: '2026-10-12T01:02:03.000000Z',
    policy: {
      version: 'ffqsv2_exact_join/v1',
      fingerprint: '6e4ba04cf9c775ac280ba1426985246ffbdf730222b4521c4b26a41f5623871a'
    },
    clocks: {
      query_source_snapshot_at: '2026-10-11T22:00:00Z',
      query_recorded_at: '2026-10-11T22:30:00Z',
      query_computed_at: '2026-10-12T01:00:00Z',
      query_published_at: '2026-10-12T01:01:00Z',
      operator_verification_observed_at: '2026-10-12T01:01:30Z',
      published_at: '2026-10-12T01:02:03.000000Z'
    },
    coverage_summary: {
      coverage_scope: 'selected_raw_fact_leaves_only',
      positive_label: 'B3_selected_member_companyfacts_row_correspondence_only',
      root_cell_count: 1,
      all_leaves_attested: 1,
      partially_attested: 0,
      not_attested: 0,
      not_evaluable: 0
    },
    companyfacts_conversion_receipt: {
      receipt_id: 'cffledger_' + hex64('a24-ledger'),
      schema: 'fundamental_forensics.companyfacts_ledger_receipt/v2',
      adapter_version: 'fixture-adapter/1',
      capture_id: 'ffseccfc_' + hex64('a24-capture'),
      manifest_id: 'ffseccfm_' + hex64('a24-manifest'),
      cik: '0000320193',
      clocks: {
        acquisition_started_at: '2026-10-11T21:00:00Z',
        captured_at: '2026-10-11T21:30:00Z',
        recorded_at: '2026-10-11T21:40:00Z',
        source_snapshot_at: '2026-10-11T21:20:00Z',
        submissions_recorded_at: '2026-10-11T21:45:00Z'
      },
      availability: 'available',
      occurrence_count: 5,
      output_occurrence_count: 5,
      pit_eligible_count: 3
    },
    authority: {
      positive_claim: 'B3_selected_member_companyfacts_row_correspondence_only',
      coverage_scope: 'selected_raw_fact_leaves_only',
      claim_basis: 'sealed_publication_receipt',
      source_reverified_at_read: false,
      match_body_replayed_at_read: false,
      nonclaims: {
        filing_complete: false,
        trading_authority: false,
        neural_web_authority: false
      }
    }
  };
}

// ── harness ─────────────────────────────────────────────────────────────────

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
      }
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
    insertAdjacentHTML(position, html) {
      if (position === 'afterbegin') this.innerHTML = html + this.innerHTML;
      else this.innerHTML += html;
    }
  };
}

function listenerElement() {
  const base = element();
  const handlers = {};
  base.addEventListener = (name, handler) => {
    handlers[name] = handlers[name] || [];
    handlers[name].push(handler);
  };
  base.handlers = handlers;
  return base;
}

const NODE_IDS = [
  'ff-workspace', 'ff-main', 'ff-as-of', 'ff-source-snapshot', 'ff-freshness-status',
  'ff-run-meta', 'ff-source-label', 'ff-desk-header', 'ff-desk-stamp', 'ff-desk-asof',
  'ff-asof-latest', 'ff-asof-input', 'ff-export-link', 'ff-export-btn', 'ff-desk-export',
  'ff-stat-coverage-label', 'ff-company-search', 'ff-company-search-clear',
  'ff-company-options', 'ff-company-identity', 'ff-company-action', 'ff-data-notice',
  'ff-overview', 'ff-overview-status', 'ff-quick-signal', 'ff-quick-signal-label',
  'ff-quick-signal-title', 'ff-quick-signal-summary', 'ff-quick-signal-magnitude',
  'ff-stat-attention', 'ff-stat-watch', 'ff-stat-coverage', 'ff-stat-sources',
  'ff-view-status', 'ff-priority-filters', 'ff-topic-select', 'ff-filter-summary',
  'ff-findings', 'ff-statements', 'ff-disclosure-section', 'ff-disclosure-summary',
  'ff-disclosure-feed', 'ff-redline-summary', 'ff-redline-list', 'ff-timeline',
  'ff-current-period', 'ff-prior-period', 'ff-compare-grid', 'ff-trace',
  'ff-revisions-table',
  'ff-source-panel-map', 'ff-source-panel-receipt', 'ff-receipt', 'ff-evidence',
  'ff-evidence-title', 'ff-evidence-body', 'ff-evidence-close', 'ff-receipt-inspector',
  'ff-receipt-inspector-title', 'ff-receipt-inspector-body', 'ff-receipt-inspector-close',
  'ff-scrim', 'ff-gate-state', 'ff-gate-preview'
];

// A fetch response whose read methods are counted, so a test can prove a
// failure branch never consumed (let alone rendered) the locked body.
function httpResponse(plan) {
  const bodyText = plan.body == null ? '' : String(plan.body);
  const reads = { arrayBuffer: 0, json: 0, text: 0, blob: 0 };
  const headers = plan.headers || {};
  const buffer = Buffer.from(bodyText, 'utf8');
  return {
    reads,
    ok: plan.status >= 200 && plan.status < 300,
    status: plan.status,
    headers: { get: (name) => headers[String(name)] || '' },
    arrayBuffer() {
      reads.arrayBuffer += 1;
      return Promise.resolve(buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength));
    },
    json() {
      reads.json += 1;
      return Promise.resolve(JSON.parse(bodyText));
    },
    text() {
      reads.text += 1;
      return Promise.resolve(bodyText);
    },
    blob() {
      reads.blob += 1;
      return Promise.resolve({});
    }
  };
}

// routes: [{ match: '/api/forensics/state', reject: true } |
//          { match: ..., respond: { status, headers, body } }] — first match
// wins; an unplanned URL hangs (inert, still counted in the census).
function mount(options) {
  options = options || {};
  const routes = options.routes || [];
  const fetchLog = [];
  const responses = [];
  const fetchFn = (url, init) => {
    const target = String(url);
    fetchLog.push({ url: target, body: init && init.body ? String(init.body) : '', method: init && init.method });
    const route = routes.find((candidate) => target.indexOf(candidate.match) >= 0);
    if (!route) return new Promise(() => {});
    if (route.reject) return Promise.reject(new TypeError('network'));
    const response = httpResponse(route.respond);
    responses.push({ url: target, response });
    return Promise.resolve(response);
  };

  const nodes = {};
  for (const id of NODE_IDS) nodes[id] = element();
  nodes['ff-gate'] = listenerElement();
  const documentObject = {
    readyState: 'loading',
    addEventListener() {},
    getElementById: (id) => nodes[id] || element(),
    querySelector() { return element(); },
    querySelectorAll() { return []; },
    createElement: () => element(),
    body: { classList: { add() {}, remove() {} }, innerHTML: '', textContent: '' },
    documentElement: { getAttribute() { return 'en'; } },
    activeElement: null
  };
  const windowObject = {
    location: {
      hostname: 'contract.test',
      pathname: '/fundamental_forensics.html',
      search: '',
      hash: '',
      href: 'https://contract.test/fundamental_forensics.html'
    },
    matchMedia: () => ({ matches: true, addEventListener() {}, addListener() {} }),
    __FF_WORKBENCH_TEST__: true,
    requestAnimationFrame(fn) { fn(); },
    setTimeout(fn) { fn(); },
    addEventListener() {},
    history: { pushState() {}, replaceState() {} },
    fetch: fetchFn,
    URL,
    URLSearchParams,
    TextDecoder,
    crypto: webcrypto
  };
  const context = vm.createContext({
    window: windowObject,
    document: documentObject,
    console,
    URL,
    URLSearchParams,
    TextDecoder,
    fetch: fetchFn,
    crypto: webcrypto,
    Response,
    Blob
  });
  vm.runInContext(PAGE_SOURCE, context, { filename: 'fundamental_forensics.js' });
  const api = windowObject.__FF_WORKBENCH_TEST__;
  api.cacheUi();
  api.bindEvents();
  api.state.payload = bundlePayload();
  api.state.symbol = 'AAPL';
  api.state.access = 'open';
  // The successful first render: setCompany renders the company, findings,
  // drawer and trace (its loadHealth side fetch follows the routes above).
  api.setCompany('AAPL', false);
  api.state.statements = mixedStatements();
  api.renderStatementTree();
  return { api, nodes, documentObject, fetchLog, responses, routes };
}

async function settle() {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1));
  }
}

// The gate's delegated Retry button is the only reachable loadData() trigger
// (templates :5403-5410); drive it exactly as a click would.
function clickGateRetry(drive) {
  const handlers = drive.nodes['ff-gate'].handlers;
  assert.ok(handlers.click && handlers.click.length >= 1, 'the gate click handler is bound');
  handlers.click[handlers.click.length - 1]({
    target: {
      closest: (selector) => (selector === '[data-gate-action]'
        ? { getAttribute: (key) => (key === 'data-gate-action' ? 'retry' : null) }
        : null)
    }
  });
}

function renderedText(drive) {
  const parts = [];
  for (const id of Object.keys(drive.nodes)) {
    parts.push(String(drive.nodes[id].innerHTML || ''), String(drive.nodes[id].textContent || ''));
  }
  parts.push(String(drive.documentObject.body.innerHTML || ''), String(drive.documentObject.body.textContent || ''));
  return parts.join('\n');
}

function assertNoLockedBytes(drive, where) {
  const all = renderedText(drive);
  assert.equal(all.includes(SENTINEL), false, where + ': the sentinel rendered');
  assert.equal(all.includes(LOCKED_RECEIPT_ID), false, where + ': the locked receipt id rendered');
}

const PAGE_URL_PREFIXES = [
  '/api/forensics/state',
  '/api/forensics/health',
  '/api/forensics/v1/financial/query',
  '/api/forensics/v1/financial/revisions',
  '/api/forensics/v1/financial/statements',
  '/api/forensics/v1/attested-history'
];

function assertFetchCensus(drive, where) {
  assert.ok(drive.fetchLog.length > 0, where + ': the stub saw no fetches');
  for (const call of drive.fetchLog) {
    assert.ok(
      PAGE_URL_PREFIXES.some((prefix) => call.url.indexOf(prefix) === 0),
      where + ': a non-page URL was fetched: ' + call.url
    );
    assert.equal(call.url.includes(SENTINEL), false, where + ': a fetched URL carries the sentinel');
    assert.equal(call.url.includes(LOCKED_RECEIPT_ID), false, where + ': a fetched URL carries the locked receipt id');
  }
}

// The compare chain needs the accepted health answer for the selected issuer
// (the mount-time loadHealth already issued seq — reuse it, pf_page style).
function seedAcceptedHealth(drive) {
  drive.api.state.health = { status: 'current', clocks: { broad_source_at: '2026-10-11T23:59:59Z' } };
  drive.api.state.healthAnswer = { entity_id: ENTITY_ID, seq: drive.api.state.healthSeq, ok: true, pointer: '' };
}

// ── S1: bundle fetch rejects (network) after a successful first render ──────

test('S1: a bundle network failure keeps the authorized drawer and leaks no locked bytes', async () => {
  const drive = mount({ routes: [{ match: '/api/forensics/state', reject: true }] });
  const drawerBefore = drive.nodes['ff-evidence-body'].innerHTML;
  assert.ok(drawerBefore.includes('href="' + AUTH_URL + '"'), 'the authorized source href rendered first');
  assert.ok(drawerBefore.includes('FY2024 Form 10-K'), 'the authorized receipt label rendered first');

  clickGateRetry(drive);
  await settle();

  // The failure branch leaves the drawer standing: authorized text + href.
  const drawer = drive.nodes['ff-evidence-body'].innerHTML;
  assert.ok(drawer === drawerBefore, 'the authorized drawer is unchanged by the load failure');
  assert.ok(drawer.includes('href="' + AUTH_URL + '"'), 'the authorized source href still resolves');
  assert.ok(drive.nodes['ff-evidence-title'].innerHTML.includes('Authorized revenue signal'),
    'the authorized node text still resolves');
  // The load failure routes through showLoadError -> GATE_COPY.unavailable.
  assert.equal(drive.nodes['ff-gate-state'].getAttribute('data-state'), 'unavailable');
  assert.ok(drive.nodes['ff-gate-state'].innerHTML.includes('Data is being refreshed'), 'the 503/unavailable gate copy');
  assert.ok(drive.nodes['ff-gate-state'].innerHTML.includes('data-gate-action="retry"'), 'the gate Retry button');
  assert.equal(drive.nodes['ff-gate'].hidden, false, 'the gate is shown');
  assertNoLockedBytes(drive, 'S1');
  assertFetchCensus(drive, 'S1');
  assert.ok(drive.fetchLog.some((call) => call.url.indexOf('/api/forensics/state') === 0), 'the bundle fetch was issued');
});

// ── S2: bundle fetch resolves 503 with a body carrying the sentinel ────────

test('S2: a bundle 503 with a sentinel body shows the gate copy, never the body', async () => {
  const drive = mount({
    routes: [{
      match: '/api/forensics/state',
      respond: { status: 503, body: '{"companies":{"AAPL":{"name":"' + SENTINEL + '"}}}' }
    }]
  });
  clickGateRetry(drive);
  await settle();

  assert.equal(drive.nodes['ff-gate-state'].getAttribute('data-state'), 'unavailable');
  assert.ok(drive.nodes['ff-gate-state'].innerHTML.includes('Data is being refreshed'),
    'the exact 503 gate copy');
  assert.ok(drive.nodes['ff-gate-state'].innerHTML.includes('Nothing is wrong with your account. Try again in a few minutes.'),
    'the exact 503 gate stance');
  assert.ok(drive.nodes['ff-gate-state'].innerHTML.includes('data-gate-action="retry"'), 'the gate Retry button');
  assert.ok(drive.nodes['ff-view-status'].innerHTML.includes('Data is being refreshed'), 'the view status copy');
  assertNoLockedBytes(drive, 'S2');
  assertFetchCensus(drive, 'S2');
  const stateResponse = drive.responses.find((entry) => entry.url.indexOf('/api/forensics/state') === 0);
  assert.ok(stateResponse, 'the 503 answer was received');
  assert.deepEqual(stateResponse.response.reads, { arrayBuffer: 0, json: 0, text: 0, blob: 0 },
    'the failing body was never consumed');
});

// ── S3: health fetch rejects ────────────────────────────────────────────────

test('S3: a health network failure shows the Unavailable badge, authorized panel intact', async () => {
  const drive = mount({ routes: [{ match: '/api/forensics/health', reject: true }] });
  await settle();

  assert.equal(drive.nodes['ff-run-meta'].getAttribute('data-freshness'), 'unavailable');
  assert.ok(drive.nodes['ff-freshness-status'].innerHTML.includes('Unavailable'), 'the freshness failure state');
  assert.ok(drive.nodes['ff-freshness-status'].innerHTML.includes('不可用'), 'the zh freshness failure state');
  // The data panel still carries the authorized node and its trace.
  const statements = drive.nodes['ff-statements'].innerHTML;
  assert.ok(statements.includes('CONSOLIDATED STATEMENTS OF OPERATIONS'), 'the authorized statement stands');
  assert.ok(statements.includes('data-occurrence-id="' + AUTH_OCCURRENCE + '"'), 'the authorized receipt id stands');
  assert.ok(drive.nodes['ff-evidence-body'].innerHTML.includes('href="' + AUTH_URL + '"'),
    'the authorized source href still resolves');
  assertNoLockedBytes(drive, 'S3');
  assertFetchCensus(drive, 'S3');
});

// ── S4: query/export fetch failures (:2032/:2052/:3379/:3413) ───────────────

test('S4a: compare-chain network rejections render the revisions error copy', async () => {
  const drive = mount({
    routes: [
      { match: '/api/forensics/v1/financial/query', reject: true },
      { match: '/api/forensics/v1/financial/revisions', reject: true }
    ]
  });
  const traceBefore = drive.nodes['ff-trace'].innerHTML;
  seedAcceptedHealth(drive);
  drive.api.setTab('compare', false);
  await settle();

  const revisions = drive.nodes['ff-revisions-table'].innerHTML;
  assert.ok(revisions.includes('Revisions temporarily unavailable'), 'the error copy renders');
  assert.ok(revisions.includes('data-financial-retry="1"'), 'the Retry control renders');
  assert.equal(drive.api.state.financial.phase, 'error');
  assert.equal(drive.api.state.financial.errorStatus, undefined, 'a network failure carries no status');
  assert.equal(drive.nodes['ff-trace'].innerHTML, traceBefore, 'the trace panel is untouched');
  assert.ok(drive.nodes['ff-trace'].innerHTML.includes('href="' + AUTH_URL + '"'),
    'the authorized source href is unchanged');
  assertNoLockedBytes(drive, 'S4a');
  assertFetchCensus(drive, 'S4a');
});

test('S4b: compare-chain 500 answers with a sentinel detail render the error copy only', async () => {
  const drive = mount({
    routes: [
      { match: '/api/forensics/v1/financial/query', respond: { status: 500, body: '{"detail":"' + SENTINEL + '"}' } },
      { match: '/api/forensics/v1/financial/revisions', respond: { status: 500, body: '{"detail":"' + SENTINEL + '"}' } }
    ]
  });
  const traceBefore = drive.nodes['ff-trace'].innerHTML;
  seedAcceptedHealth(drive);
  drive.api.setTab('compare', false);
  await settle();

  const revisions = drive.nodes['ff-revisions-table'].innerHTML;
  assert.ok(revisions.includes('Revisions temporarily unavailable'), 'the error copy renders');
  assert.ok(revisions.includes('data-financial-retry="1"'), 'the Retry control renders');
  assert.equal(drive.api.state.financial.phase, 'error');
  assert.equal(drive.api.state.financial.errorStatus, 500);
  assert.equal(drive.api.state.financial.errorDetail, SENTINEL, 'the detail drives copy choice only');
  assert.equal(drive.nodes['ff-trace'].innerHTML, traceBefore, 'the trace panel is untouched');
  assert.ok(drive.nodes['ff-trace'].innerHTML.includes('href="' + AUTH_URL + '"'),
    'the authorized source href is unchanged');
  assertNoLockedBytes(drive, 'S4b');
  assertFetchCensus(drive, 'S4b');
});

test('S4c: an export 500 disables Export without reading or rendering the body', async () => {
  const drive = mount({
    routes: [{
      match: '/api/forensics/v1/financial/query.xlsx',
      respond: { status: 500, body: '{"detail":"' + SENTINEL + '"}' }
    }]
  });
  drive.api.applyHealth({ status: 'current', clocks: { broad_source_at: '2026-10-11T23:59:59Z' } });
  assert.equal(drive.nodes['ff-export-btn'].disabled, false, 'Export starts ready');
  drive.api.runExport();
  await settle();

  assert.equal(drive.nodes['ff-export-btn'].disabled, true, 'Export ends disabled');
  assert.ok(drive.nodes['ff-export-btn'].innerHTML.includes('Export unavailable'), 'the failure copy renders');
  assert.equal(drive.nodes['ff-export-btn'].getAttribute('aria-label'), 'Export unavailable');
  assert.ok(String(drive.nodes['ff-export-btn'].getAttribute('data-tip-en')).includes('the last download request failed'),
    'the failure tip names the failed request');
  assertNoLockedBytes(drive, 'S4c');
  assertFetchCensus(drive, 'S4c');
  const exportResponse = drive.responses.find((entry) => entry.url.indexOf('/api/forensics/v1/financial/query.xlsx') === 0);
  assert.ok(exportResponse, 'the export 500 answer was received');
  assert.deepEqual(exportResponse.response.reads, { arrayBuffer: 0, json: 0, text: 0, blob: 0 },
    'the failing export body was never consumed');
});

// ── S5: attested-history fetch failures (:4407/:4495/:4527) ─────────────────

test('S5a: an attested-history /latest network rejection renders the unavailable copy', async () => {
  const drive = mount({ routes: [{ match: '/api/forensics/v1/attested-history/latest', reject: true }] });
  const traceBefore = drive.nodes['ff-trace'].innerHTML;
  drive.api.state.sourceMode = 'receipt';
  drive.api.setTab('trace', false);
  await settle();

  const receipt = drive.nodes['ff-receipt'].innerHTML;
  assert.ok(receipt.includes('Run record temporarily unavailable'), 'the error copy renders');
  assert.ok(receipt.includes('data-receipt-action="retry"'), 'the Retry control renders');
  assert.equal(drive.api.state.receipt.phase, 'unavailable');
  assert.equal(drive.nodes['ff-trace'].innerHTML, traceBefore, 'the trace panel is untouched');
  assert.ok(drive.nodes['ff-trace'].innerHTML.includes('href="' + AUTH_URL + '"'),
    'the authorized source href is unchanged');
  assertNoLockedBytes(drive, 'S5a');
  assertFetchCensus(drive, 'S5a');
});

test('S5b: an attested-history /latest 500 with a sentinel body renders the copy only', async () => {
  const drive = mount({
    routes: [{
      match: '/api/forensics/v1/attested-history/latest',
      respond: { status: 500, body: '{"snapshot_id":"' + SENTINEL + '"}' }
    }]
  });
  drive.api.state.sourceMode = 'receipt';
  drive.api.setTab('trace', false);
  await settle();

  const receipt = drive.nodes['ff-receipt'].innerHTML;
  assert.ok(receipt.includes('Run record temporarily unavailable'), 'the error copy renders');
  assert.ok(receipt.includes('data-receipt-action="retry"'), 'the Retry control renders');
  assert.equal(drive.api.state.receipt.phase, 'unavailable');
  assertNoLockedBytes(drive, 'S5b');
  assertFetchCensus(drive, 'S5b');
  const latest = drive.responses.find((entry) => entry.url.indexOf('/attested-history/latest') >= 0);
  assert.deepEqual(latest.response.reads, { arrayBuffer: 0, json: 0, text: 0, blob: 0 },
    'the failing history body was never consumed');
});

test('S5c: a roots rejection after a good /latest renders the unavailable copy', async () => {
  const drive = mount({
    routes: [
      { match: '/api/forensics/v1/attested-history/latest', respond: { status: 200, body: JSON.stringify(latestReceiptPayload()) } },
      { match: '/api/forensics/v1/attested-history/snapshots', reject: true }
    ]
  });
  drive.api.state.sourceMode = 'receipt';
  drive.api.setTab('trace', false);
  await settle();

  const receipt = drive.nodes['ff-receipt'].innerHTML;
  assert.ok(receipt.includes('Run record temporarily unavailable'), 'the error copy renders');
  assert.ok(receipt.includes('data-receipt-action="retry"'), 'the Retry control renders');
  assert.equal(drive.api.state.receipt.phase, 'unavailable');
  // The accepted /latest identity is held in state but never rendered as data.
  assert.ok(drive.api.state.receipt.latest, 'the accepted latest answer is held');
  assertNoLockedBytes(drive, 'S5c');
  assertFetchCensus(drive, 'S5c');
  const roots = drive.fetchLog.find((call) => call.url.indexOf('/api/forensics/v1/attested-history/snapshots/') === 0);
  assert.ok(roots, 'the roots leg was issued');
  assert.ok(/\/snapshots\/ffqsv2_[a-f0-9]{64}\/roots\?limit=25$/.test(roots.url), 'the roots URL is page-constructed');
});

// ── S6: the withheld node's private receipt digest never renders ────────────

test('S6: a missing node\'s private receipt digest never renders; the authorized receipt does', async () => {
  const drive = mount();
  await settle(); // the mount-time health fetch enters the census
  const nodes = [authorizedQueryNode(), lockedQueryNode()];
  drive.api.state.queryNodes = nodes;
  drive.api.state.health = { status: 'current', clocks: { broad_source_at: '2026-10-11T23:59:59Z' } };
  drive.api.state.financial = {
    phase: 'ready',
    asReported: nodes,
    latest: nodes,
    restated: nodes,
    revisions: [],
    receiptPolicy: {}
  };
  drive.api.renderRevisions();

  const html = drive.nodes['ff-revisions-table'].innerHTML;
  assert.ok(html.includes('data-occurrence-id="' + AUTH_OCCURRENCE + '"'),
    'the authorized node\'s receipt renders as the page intends');
  assert.ok(html.includes('No value at this cutoff'), 'the locked node renders its absence copy');

  // The authorized control's drawer proves the receipt trace resolves end to
  // end while the locked node's digest never reaches the DOM.
  const control = {
    disabled: false,
    getAttribute: (key) => ({
      'data-source-kind': 'cell',
      'data-occurrence-id': AUTH_OCCURRENCE,
      'data-root-cell-id': AUTH_ROOT_CELL,
      'data-snapshot-id': AUTH_SNAPSHOT,
      'data-accession': AUTH_ACCESSION,
      'data-span-start': '12',
      'data-span-end': '48'
    })[key] || null,
    querySelector: () => null
  };
  const cell = drive.api.cellEvidenceFromControl(control);
  assert.equal(cell.exactText, '416161000000', 'the authorized exact value attaches');
  drive.api.renderCellEvidence(cell);
  const drawer = drive.nodes['ff-evidence-body'].innerHTML;
  assert.ok(drawer.includes('<code class="ff-exact">416161000000</code>'), 'the authorized value renders');
  assert.ok(drawer.includes('title="' + AUTH_OCCURRENCE + '"'), 'the authorized receipt id renders as intended');
  assertNoLockedBytes(drive, 'S6');
  assertFetchCensus(drive, 'S6');
});

// ── S7: the fetch census across every failing lane ──────────────────────────

test('S7: every fetched URL is page-constructed; none carries locked bytes', async () => {
  const drive = mount({
    routes: [
      { match: '/api/forensics/state', respond: { status: 503, body: '{"detail":"' + SENTINEL + '"}' } },
      { match: '/api/forensics/health', reject: true },
      { match: '/api/forensics/v1/financial/query.xlsx', respond: { status: 500, body: SENTINEL } },
      { match: '/api/forensics/v1/financial/query', respond: { status: 500, body: '{"detail":"' + SENTINEL + '"}' } },
      { match: '/api/forensics/v1/financial/revisions', respond: { status: 500, body: '{"detail":"' + SENTINEL + '"}' } },
      { match: '/api/forensics/v1/attested-history/latest', respond: { status: 200, body: JSON.stringify(latestReceiptPayload()) } },
      { match: '/api/forensics/v1/attested-history/snapshots', reject: true }
    ]
  });
  await settle(); // the mount-time health fetch rejects
  clickGateRetry(drive); // the bundle lane
  await settle();
  // Re-open the desk the gate closed, then drive the remaining lanes.
  drive.api.state.access = 'open';
  seedAcceptedHealth(drive);
  drive.api.setTab('compare', false);
  await settle();
  drive.api.applyHealth({ status: 'current', clocks: { broad_source_at: '2026-10-11T23:59:59Z' } });
  drive.api.runExport();
  drive.api.state.sourceMode = 'receipt';
  drive.api.setTab('trace', false);
  await settle();

  assertFetchCensus(drive, 'S7');
  const urls = drive.fetchLog.map((call) => call.url);
  assert.ok(urls.some((url) => url.indexOf('/api/forensics/state') === 0), 'the bundle URL was fetched');
  assert.ok(urls.some((url) => url.indexOf('/api/forensics/health?entity_id=') === 0), 'the health URL was fetched');
  assert.ok(urls.filter((url) => url.indexOf('/api/forensics/v1/financial/query') === 0).length >= 3,
    'the three compare legs were fetched');
  assert.ok(urls.some((url) => url.indexOf('/api/forensics/v1/financial/revisions') === 0), 'the revisions leg was fetched');
  assert.ok(urls.some((url) => url.indexOf('/api/forensics/v1/financial/query.xlsx') === 0), 'the export URL was fetched');
  assert.ok(urls.some((url) => url.indexOf('/api/forensics/v1/attested-history/latest') === 0), 'the history URL was fetched');
  assert.ok(urls.some((url) => url.indexOf('/api/forensics/v1/attested-history/snapshots/') === 0), 'the roots URL was fetched');
  assertNoLockedBytes(drive, 'S7');
});

// A44 — a missing source span renders the explicit unavailable state.
//
// A number whose receipt carries no recorded span must never become a link to
// a generic EDGAR page or an invented span: the statement-tree control renders
// disabled with the bilingual "Source span unavailable" copy and no span
// attributes, and the evidence drawer says the span is unavailable and links
// nowhere. A recorded span on the same cell still renders the live control.
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const PAGE_SOURCE = readFileSync(new URL('../templates/fundamental_forensics.js', import.meta.url), 'utf8');

function element() {
  const classes = new Set();
  return {
    classList: {
      add: (name) => classes.add(name),
      remove: (name) => classes.delete(name),
      contains: (name) => classes.has(name),
      toggle: (name, force) => { if (force === false || (force === undefined && classes.has(name))) classes.delete(name); else classes.add(name); },
    },
    hidden: true,
    innerHTML: '',
    textContent: '',
    style: {},
    dataset: {},
    setAttribute() {},
    getAttribute() { return null; },
    removeAttribute() {},
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    focus() {},
    contains() { return false; },
  };
}

function harness() {
  const nodes = {
    'ff-statements': element(),
    'ff-evidence': element(),
    'ff-evidence-body': element(),
    'ff-evidence-title': element(),
  };
  const documentObject = {
    readyState: 'loading',
    addEventListener() {},
    getElementById: (id) => nodes[id] || element(),
    querySelector() { return element(); },
    querySelectorAll() { return []; },
    body: { classList: { add() {}, remove() {} } },
    documentElement: { getAttribute() { return 'en'; }, setAttribute() {} },
    activeElement: null,
  };
  const windowObject = {
    location: { hostname: 'contract.test', pathname: '/fundamental_forensics.html', search: '', hash: '', href: 'https://contract.test/fundamental_forensics.html' },
    matchMedia: () => ({ matches: true, addEventListener() {}, addListener() {} }),
    __FF_WORKBENCH_TEST__: true,
    requestAnimationFrame(fn) { fn(); },
    addEventListener() {},
    history: { pushState() {}, replaceState() {} },
    fetch: () => new Promise(() => {}),
  };
  const context = vm.createContext({ window: windowObject, document: documentObject, console, URL, URLSearchParams, TextDecoder });
  vm.runInContext(PAGE_SOURCE, context, { filename: 'fundamental_forensics.js' });
  const api = windowObject.__FF_WORKBENCH_TEST__;
  api.cacheUi();
  api.ui.statements = nodes['ff-statements'];
  api.ui.evidence = nodes['ff-evidence'];
  api.ui.evidenceBody = nodes['ff-evidence-body'];
  api.ui.evidenceTitle = nodes['ff-evidence-title'];
  api.state.tab = 'statements';
  api.state.payload = { companies: { AAPL: { symbol: 'AAPL', entity_id: 'ISS:US-XNAS-AAPL', periods: [] } }, default_symbol: 'AAPL' };
  api.state.symbol = 'AAPL';
  return { api, nodes };
}

function statementCell(sourceSpan) {
  const receipt = { occurrence_id: 'occ-1', root_cell_id: 'root-1', snapshot_id: 'snap-1', accession: '0000320193-24-000123' };
  if (sourceSpan !== undefined) receipt.source_span = sourceSpan;
  return { quality_state: 'available', value: '100', unit: 'USD', source_receipt: receipt };
}

function treeWith(cells) {
  return {
    phase: 'ready',
    statements: [{
      statement_type: 'income_statement',
      title: 'Income statement',
      columns: cells.map((_, index) => ({ label: 'FY' + index, start: '2023-10-01', end: '2024-09-28' })),
      rows: [{ as_reported_label: 'Net sales', standardized_metric_id: 'revenue', cells }],
    }],
  };
}

function sourceControls(html) {
  return html.match(/<(button|span) type="button" class="ff-source-control[^"]*"[^>]*>/g) || [];
}

function control(attrs) {
  return {
    disabled: false,
    getAttribute: (key) => (Object.prototype.hasOwnProperty.call(attrs, key) ? attrs[key] : null),
    querySelector: (selector) => (selector === '.ff-compact' ? { textContent: '100' } : null),
  };
}

test('the workbench carries no generic EDGAR fallback destination', () => {
  assert.doesNotMatch(PAGE_SOURCE, /sec\.gov|edgar\/browse|cgi-bin\/browse-edgar/i);
});

test('statement tree: a cell with no recorded span renders the disabled unavailable control', () => {
  for (const missing of [undefined, null, [], [7], { start: 3 }, { char_end: 9 }, 'not-a-span']) {
    const { api, nodes } = harness();
    api.state.statements = treeWith([statementCell(missing)]);
    api.renderStatementTree();
    const html = nodes['ff-statements'].innerHTML;
    const controls = sourceControls(html);
    assert.equal(controls.length, 1, 'one control for ' + JSON.stringify(missing));
    assert.match(controls[0], /class="ff-source-control is-unavailable"/);
    assert.match(controls[0], / disabled aria-disabled="true"/);
    assert.doesNotMatch(controls[0], /data-span-start|data-span-end|href=/);
    assert.ok(html.includes('Source span unavailable'), 'English unavailable copy for ' + JSON.stringify(missing));
    assert.ok(html.includes('来源片段不可用'), 'Chinese unavailable copy for ' + JSON.stringify(missing));
    assert.doesNotMatch(html, /<a\s/i, 'no anchor for ' + JSON.stringify(missing));
  }
});

test('statement tree: a recorded span on the same cell renders the live control', () => {
  const { api, nodes } = harness();
  api.state.statements = treeWith([statementCell([12, 48]), statementCell({ char_start: 3, char_end: 9 })]);
  api.renderStatementTree();
  const controls = sourceControls(nodes['ff-statements'].innerHTML);
  assert.equal(controls.length, 2);
  for (const tag of controls) {
    assert.doesNotMatch(tag, /is-unavailable|disabled/);
  }
  assert.match(controls[0], /data-span-start="12"[^>]*data-span-end="48"/);
  assert.match(controls[1], /data-span-start="3"[^>]*data-span-end="9"/);
});

test('evidence drawer: a control with no span says so and links nowhere', () => {
  const { api, nodes } = harness();
  const cell = api.cellEvidenceFromControl(control({
    'data-source-kind': 'statement',
    'data-occurrence-id': 'occ-1',
    'data-root-cell-id': 'root-1',
    'data-snapshot-id': 'snap-1',
    'data-accession': '0000320193-24-000123',
  }));
  api.renderCellEvidence(cell);
  const body = nodes['ff-evidence-body'].innerHTML;
  assert.ok(body.includes('Source span unavailable'), 'the drawer names the missing span');
  assert.ok(body.includes('<dt>span</dt><dd><code>—</code></dd>'), 'the span field is empty, not invented');
  assert.doesNotMatch(body, /<a\s|href=/i, 'the drawer offers no fallback link');
  assert.doesNotMatch(body, /ff-span-excerpt/, 'no excerpt is fabricated');
});

// Defect (g): a compare card or a finding value links only to the query node
// for its own period. State periods are fiscal-quarter buckets whose start the
// main projection may not carry; a node answers one only for the same metric,
// the same end, the same start (or, start-less, an interval of at most one
// quarter), a value state with a span, and the very number shown (AM1).
const CURRENT_Q = { fiscal_year: 2025, fiscal_quarter: 4, label: 'FY2025 Q4', kind: 'duration', start: null, end: '2025-09-27', period_end: '2025-09-27', revenue: 102466000000 };
const PRIOR_Q = { fiscal_year: 2024, fiscal_quarter: 4, label: 'FY2024 Q4', kind: 'duration', start: null, end: '2024-09-28', period_end: '2024-09-28', revenue: 94930000000 };

function revenueNode(start, end, value, occurrenceId, span, extra) {
  return Object.assign({
    metric_id: 'revenue',
    period: { kind: 'duration', start, end },
    state: 'value',
    value,
    unit: 'USD',
    provenance: {
      accession: '0000320193-25-000079',
      selected_raw_fact: { occurrence_id: occurrenceId, source_span: span === undefined ? { start: 10, end: 40 } : span },
    },
  }, extra || {});
}

const ANNUAL_FY25 = revenueNode('2024-09-29', '2025-09-27', '102466000000', 'occ-annual', { start: 1, end: 9 });
const QUARTER_CUR = revenueNode('2025-06-29', '2025-09-27', '102466000000', 'occ-cur', { start: 100, end: 140 });
const QUARTER_PRI = revenueNode('2024-06-30', '2024-09-28', '94930000000', 'occ-pri', { start: 200, end: 240 });

function compareHarness(periods, nodes) {
  const { api } = harness();
  api.ui.compareGrid = element();
  api.state.payload.companies.AAPL.periods = periods;
  api.state.currentPeriod = 0;
  api.state.priorPeriod = 1;
  api.state.queryNodes = nodes;
  return api;
}

function revenueCardControls(api) {
  api.renderCompare(api.state.payload.companies.AAPL);
  const html = api.ui.compareGrid.innerHTML;
  const card = html.split('<article class="ff-compare-card">')[1] || '';
  assert.ok(card.includes('Revenue'), 'the first card is revenue');
  return sourceControls(card);
}

test('compare: each card binds its own period\'s quarter node, never the annual one', () => {
  const api = compareHarness([CURRENT_Q, PRIOR_Q], [ANNUAL_FY25, QUARTER_PRI, QUARTER_CUR]);
  const [current, prior] = revenueCardControls(api);
  assert.match(current, /data-occurrence-id="occ-cur"[^>]*data-span-start="100"[^>]*data-span-end="140"/);
  assert.match(prior, /data-occurrence-id="occ-pri"[^>]*data-span-start="200"[^>]*data-span-end="240"/);
  assert.doesNotMatch(current + prior, /occ-annual|is-unavailable/);
});

test('compare: a start-less quarter row never borrows an annual node or another period', () => {
  const cases = [
    ['annual interval only', [ANNUAL_FY25]],
    ['prior-period node only', [revenueNode('2024-06-30', '2024-09-28', '102466000000', 'occ-x')]],
    ['value differs from the shown number (AM1)', [revenueNode('2025-06-29', '2025-09-27', '102466000001', 'occ-x')]],
    ['JSON number instead of decimal text', [revenueNode('2025-06-29', '2025-09-27', 102466000000, 'occ-x')]],
    ['non-value state', [revenueNode('2025-06-29', '2025-09-27', '102466000000', 'occ-x', undefined, { state: 'not_reported' })]],
    ['no recorded span', [revenueNode('2025-06-29', '2025-09-27', '102466000000', 'occ-x', null)]],
    ['another metric', [revenueNode('2025-06-29', '2025-09-27', '102466000000', 'occ-x', undefined, { metric_id: 'gross_profit' })]],
  ];
  for (const [name, nodes] of cases) {
    const api = compareHarness([CURRENT_Q, PRIOR_Q], nodes);
    const [current] = revenueCardControls(api);
    assert.match(current, /class="ff-source-control is-unavailable"/, name);
    assert.doesNotMatch(current, /data-occurrence-id|data-span-start/, name);
  }
});

test('compare: a row that carries its start binds the node with that exact start', () => {
  const annualRow = Object.assign({}, CURRENT_Q, { label: 'FY2025', fiscal_quarter: null, start: '2024-09-29' });
  const api = compareHarness([annualRow, PRIOR_Q], [QUARTER_CUR, ANNUAL_FY25]);
  const [current] = revenueCardControls(api);
  assert.match(current, /data-occurrence-id="occ-annual"/);
  const shifted = compareHarness([Object.assign({}, annualRow, { start: '2024-10-01' })], [ANNUAL_FY25]);
  assert.match(revenueCardControls(shifted)[0], /is-unavailable/);
});

test('finding values resolve to the finding\'s own current and prior periods', () => {
  const api = compareHarness([CURRENT_Q, PRIOR_Q], [ANNUAL_FY25, QUARTER_PRI, QUARTER_CUR]);
  const value = { key: 'revenue', label: 'Revenue', current: 102466000000, prior: 94930000000, delta: 7536000000, format: 'currency' };
  const finding = { title: 'Revenue step-up', period_current: 'FY2025 Q4', period_prior: 'FY2024 Q4', values: [value] };
  const current = api.valueControlOpts(value, 'current', finding);
  const prior = api.valueControlOpts(value, 'prior', finding);
  const delta = api.valueControlOpts(value, 'delta', finding);
  assert.equal(current.occurrenceId, 'occ-cur');
  assert.equal(current.exactText, '102466000000');
  assert.equal(prior.occurrenceId, 'occ-pri');
  assert.equal(prior.exactText, '94930000000');
  assert.equal(delta.occurrenceId, 'occ-cur', 'the change opens the current period\'s span');
  assert.equal(delta.kind, 'finding');
  api.renderEvidence(finding);
  const body = api.ui.evidenceBody.innerHTML;
  assert.match(body, /data-occurrence-id="occ-cur"/);
  assert.match(body, /data-occurrence-id="occ-pri"/);
  assert.doesNotMatch(body, /occ-annual/);
});

test('finding values with no matching state period stay unavailable (no period-agnostic fallback)', () => {
  const api = compareHarness([CURRENT_Q, PRIOR_Q], [ANNUAL_FY25, QUARTER_PRI, QUARTER_CUR]);
  const value = { key: 'revenue', current: 102466000000, prior: 94930000000, delta: 7536000000, format: 'currency' };
  for (const finding of [{ period_current: 'FY2025', period_prior: 'FY2024' }, {}, { period_current: 'FY2023 Q4', period_prior: 'FY2022 Q4' }]) {
    for (const which of ['current', 'prior', 'delta']) {
      const opts = api.valueControlOpts(value, which, finding);
      assert.equal(opts.occurrenceId, undefined, which + ' ' + JSON.stringify(finding));
      assert.equal(opts.kind, 'finding');
    }
  }
  assert.equal(api.queryNodeForValue(value, 'FY2025 Q4', 102466000000).provenance.selected_raw_fact.occurrence_id, 'occ-cur');
  assert.equal(api.queryNodeForValue({ key: 'unknown_metric' }, 'FY2025 Q4', 102466000000), null);
});

function fetchHarness(respond) {
  const nodes = {
    'ff-statements': element(),
    'ff-evidence': element(),
    'ff-evidence-body': element(),
    'ff-evidence-title': element(),
  };
  const documentObject = {
    readyState: 'loading',
    addEventListener() {},
    getElementById: (id) => nodes[id] || element(),
    querySelector() { return element(); },
    querySelectorAll() { return []; },
    body: { classList: { add() {}, remove() {} } },
    documentElement: { getAttribute() { return 'en'; }, setAttribute() {} },
    activeElement: null,
  };
  const fetchImpl = (url, init) => respond(String(url), init);
  const windowObject = {
    location: { hostname: 'localhost', pathname: '/fundamental_forensics.html', search: '', hash: '', href: 'http://localhost/fundamental_forensics.html' },
    matchMedia: () => ({ matches: true, addEventListener() {}, addListener() {} }),
    __FF_WORKBENCH_TEST__: true,
    requestAnimationFrame(fn) { fn(); },
    addEventListener() {},
    history: { pushState() {}, replaceState() {} },
    fetch: fetchImpl,
    crypto: webcrypto,
  };
  const context = vm.createContext({ window: windowObject, document: documentObject, console, URL, URLSearchParams, TextDecoder, fetch: fetchImpl, crypto: webcrypto });
  vm.runInContext(PAGE_SOURCE, context, { filename: 'fundamental_forensics.js' });
  const api = windowObject.__FF_WORKBENCH_TEST__;
  api.cacheUi();
  api.ui.statements = nodes['ff-statements'];
  api.state.payload = { companies: { AAPL: { symbol: 'AAPL', entity_id: 'ISS:US-XNAS-AAPL', periods: [] } }, default_symbol: 'AAPL' };
  api.state.symbol = 'AAPL';
  api.state.queryNodes = [{ provenance: { accession: '0000320193-25-000079' } }];
  return api;
}

function deferredStatements() {
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  // The page verifies X-FIF-Response-SHA256 against the raw body (A38), so
  // the stub reply carries the true digest of its bytes.
  const body = Buffer.from(JSON.stringify({ statements: [{ statement_type: 'income_statement', title: 'Income statement', columns: [], rows: [] }] }));
  const digest = createHash('sha256').update(body).digest('hex');
  const respond = (url) => {
    if (url.indexOf('/financial/statements') < 0) return new Promise(() => {});
    return gate.then(() => ({
      ok: true,
      status: 200,
      headers: { get: (name) => (String(name).toLowerCase() === 'x-fif-response-sha256' ? digest : null) },
      arrayBuffer: async () => body.buffer.slice(body.byteOffset, body.byteOffset + body.byteLength),
    }));
  };
  return { respond, release: () => release() };
}

async function settle() {
  for (let index = 0; index < 20; index += 1) await new Promise((resolve) => setImmediate(resolve));
}

test('statements keep their own load token: a compare load mid-flight does not strand them', async () => {
  const gate = deferredStatements();
  const api = fetchHarness(gate.respond);
  api.state.tab = 'statements';
  api.ensureStatements();
  assert.equal(api.state.statements.phase, 'loading');
  const before = api.state.financialToken;
  api.state.tab = 'compare';
  api.ensureFinancialData();
  assert.ok(api.state.financialToken > before, 'the compare chain took a new financial token');
  gate.release();
  await settle();
  assert.equal(api.state.statements.phase, 'ready', 'the statement reply still lands');
});

test('statements: a reset while a reply is in flight discards that reply', async () => {
  const gate = deferredStatements();
  const api = fetchHarness(gate.respond);
  api.state.tab = 'statements';
  api.ensureStatements();
  api.resetStatementsState();
  gate.release();
  await settle();
  assert.equal(api.state.statements.phase, 'idle');
});

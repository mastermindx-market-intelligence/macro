// A44 — a missing source span renders the explicit unavailable state.
//
// A number whose receipt carries no recorded span must never become a link to
// a generic EDGAR page or an invented span: the statement-tree control renders
// disabled with the bilingual "Source span unavailable" copy and no span
// attributes, and the evidence drawer says the span is unavailable and links
// nowhere. A recorded span on the same cell still renders the live control.
import assert from 'node:assert/strict';
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

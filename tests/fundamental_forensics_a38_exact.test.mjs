import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../templates/fundamental_forensics.js', import.meta.url), 'utf8');

function element() {
  const classes = new Set();
  const attrs = {};
  return {
    classList: {
      add: (name) => classes.add(name),
      remove: (name) => classes.delete(name),
      contains: (name) => classes.has(name),
    },
    hidden: true,
    innerHTML: '',
    textContent: '',
    setAttribute: (key, value) => {
      attrs[key] = String(value);
    },
    removeAttribute: (key) => {
      delete attrs[key];
    },
    getAttribute: (key) => (Object.prototype.hasOwnProperty.call(attrs, key) ? attrs[key] : null),
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    focus() {},
  };
}

function harness() {
  const nodes = {
    'ff-evidence': element(),
    'ff-evidence-body': element(),
    'ff-evidence-title': element(),
    'ff-workspace': element(),
    'ff-scrim': element(),
    'ff-main': element(),
  };
  const documentObject = {
    readyState: 'loading',
    addEventListener() {},
    getElementById: (id) => nodes[id] || element(),
    querySelector() { return element(); },
    querySelectorAll() { return []; },
    body: { classList: { add() {}, remove() {} } },
    documentElement: { getAttribute() { return 'en'; } },
    activeElement: null,
  };
  const windowObject = {
    location: { hostname: 'contract.test', pathname: '/fundamental_forensics.html', search: '', hash: '' },
    matchMedia: () => ({ matches: true, addEventListener() {}, addListener() {} }),
    __FF_WORKBENCH_TEST__: true,
    requestAnimationFrame(fn) { fn(); },
    addEventListener() {},
    history: { pushState() {}, replaceState() {} },
    fetch: () => new Promise(() => {}),
  };
  const context = vm.createContext({
    window: windowObject,
    document: documentObject,
    console,
    URL,
    URLSearchParams,
    TextDecoder,
  });
  vm.runInContext(source, context, { filename: 'fundamental_forensics.js' });
  const api = windowObject.__FF_WORKBENCH_TEST__;
  api.cacheUi();
  api.ui.evidence = nodes['ff-evidence'];
  api.ui.evidenceBody = nodes['ff-evidence-body'];
  api.ui.evidenceTitle = nodes['ff-evidence-title'];
  api.ui.workspace = nodes['ff-workspace'];
  api.ui.scrim = nodes['ff-scrim'];
  api.ui.main = nodes['ff-main'];
  api.ui.siteNav = element();
  return { api, nodes };
}

function fixtureControl(attrs) {
  const values = Object.assign({
    'data-source-kind': 'cell',
    'data-occurrence-id': 'rawfact_fixture0001',
    'data-root-cell-id': 'metric_cell_fixture01',
    'data-snapshot-id': 'ffqsv2_fixture0001',
    'data-accession': '0000320193-25-000073',
    'data-span-start': '1234',
    'data-span-end': '1288',
  }, attrs || {});
  return {
    disabled: false,
    getAttribute: (key) => (Object.prototype.hasOwnProperty.call(values, key) ? values[key] : null),
    querySelector: (selector) => (selector === '.ff-compact' ? { textContent: '$94.9B' } : null),
  };
}

function fixtureNode(value) {
  return {
    cell_id: 'metric_cell_fixture01',
    metric_id: 'revenue',
    value,
    unit: 'USD',
    display_excerpt: 'Total net sales … 94,936 …',
    provenance: {
      accession: '0000320193-25-000073',
      selected_raw_fact: {
        occurrence_id: 'rawfact_fixture0001',
        source_span: [1234, 1288],
      },
    },
  };
}

test('exact drawer value carries the API decimal bytes unchanged', () => {
  const { api, nodes } = harness();
  api.state.queryNodes = [fixtureNode('94936000000')];
  const cell = api.cellEvidenceFromControl(fixtureControl());
  assert.equal(cell.exactText, '94936000000');
  api.renderCellEvidence(cell);
  const body = nodes['ff-evidence-body'].innerHTML;
  assert.match(body, /<code class="ff-exact">94936000000<\/code>/);
  // The compact form is the labelled secondary, never the exact display.
  assert.match(body, /Compact/);
  assert.match(body, /\$94\.9B/);
});

test('a JSON number value never renders as an exact decimal', () => {
  const { api, nodes } = harness();
  api.state.queryNodes = [fixtureNode(94936000000)];
  const cell = api.cellEvidenceFromControl(fixtureControl());
  assert.equal(cell.exactText, '');
  api.renderCellEvidence(cell);
  const body = nodes['ff-evidence-body'].innerHTML;
  assert.doesNotMatch(body, /<code class="ff-exact">94936000000<\/code>/);
  assert.doesNotMatch(body, /<code class="ff-exact">94936000000\.0*<\/code>/);
  assert.match(body, /Exact value unavailable/);
});

test('the occurrence id rides a code element whose title is the id only', () => {
  const { api, nodes } = harness();
  api.state.queryNodes = [fixtureNode('94936000000')];
  const cell = api.cellEvidenceFromControl(fixtureControl());
  api.renderCellEvidence(cell);
  const body = nodes['ff-evidence-body'].innerHTML;
  assert.match(body, /<code title="rawfact_fixture0001">/);
  assert.doesNotMatch(body, /falsif/);
  assert.doesNotMatch(body, /refut/);
});

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const PAGE_SOURCE = readFileSync(new URL('../templates/fundamental_forensics.js', import.meta.url), 'utf8');

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
    },
  };
}

function harness() {
  const nodes = { 'ff-statements': element() };
  const documentObject = {
    readyState: 'loading',
    addEventListener() {},
    getElementById: (id) => nodes[id] || element(),
    querySelector() { return element(); },
    querySelectorAll() { return []; },
    body: { classList: { add() {}, remove() {} } },
    documentElement: {
      getAttribute() { return 'en'; },
      setAttribute(key, value) { this._lang = value; },
      _lang: 'en',
    },
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
    URL,
    URLSearchParams,
    TextDecoder,
  };
  const context = vm.createContext({
    window: windowObject,
    document: documentObject,
    console,
    URL,
    URLSearchParams,
    TextDecoder,
  });
  vm.runInContext(PAGE_SOURCE, context, { filename: 'fundamental_forensics.js' });
  const api = windowObject.__FF_WORKBENCH_TEST__;
  api.cacheUi();
  api.ui.statements = nodes['ff-statements'];
  api.state.tab = 'statements';
  api.state.payload = {
    companies: {
      AAPL: {
        symbol: 'AAPL',
        entity_id: 'ISS:US-XNAS-AAPL',
        periods: [{ fiscal_year: 2024, period_end: '2024-09-28', filed: '2024-11-01' }],
        disclosure_bundle: {
          tracks: [{
            current_filing: { accession: '0000320193-24-000123', form: '10-K' },
          }],
        },
      },
    },
    default_symbol: 'AAPL',
  };
  api.state.symbol = 'AAPL';
  return { api, nodes, documentObject };
}

function mixedStatements() {
  return [
    {
      statement_type: 'income_statement',
      title: 'Income',
      columns: [{ label: 'FY', start: '2023-10-01', end: '2024-09-28' }],
      rows: [{
        as_reported_label: 'Revenue',
        standardized_metric_id: 'revenue',
        cells: [{ quality_state: 'available', value: '100' }],
      }],
    },
    {
      statement_type: 'balance_sheet',
      refusal: { code: 'displayed_columns_absent' },
      columns: [],
      rows: [],
    },
  ];
}

function allRefusedStatements() {
  return ['income_statement', 'balance_sheet', 'cash_flow'].map((statement_type) => ({
    statement_type,
    refusal: { code: 'displayed_table_absent' },
    columns: [],
    rows: [],
  }));
}

test('mixed accession renders one withheld block with EN copy and ZH under zh', () => {
  const { api, documentObject, nodes } = harness();
  api.state.statements = { phase: 'ready', statements: mixedStatements() };
  api.renderStatementTree();
  const html = nodes['ff-statements'].innerHTML;
  assert.match(html, /ff-statement-block--withheld/);
  assert.match(html, /ff-statement-table/);
  assert.match(html, /rebuild this statement line by line from this filing yet/);
  assert.doesNotMatch(html, /linked above/);
  assert.match(html, /我们暂时无法从该财报逐行重建此报表/);
});

test('all-refused accession renders notice and normalized table', () => {
  const { api, nodes } = harness();
  api.state.statements = { phase: 'ready', statements: allRefusedStatements() };
  api.renderStatementTree();
  const html = nodes['ff-statements'].innerHTML;
  assert.match(html, /normalized table below still covers its figures/);
  assert.match(html, /ff-table-wrap/);
  assert.match(html, /Period \/ filed/);
});

test('refusal code message and slug never appear in rendered HTML', () => {
  const { api, nodes } = harness();
  api.state.statements = { phase: 'ready', statements: mixedStatements() };
  api.renderStatementTree();
  const html = nodes['ff-statements'].innerHTML;
  for (const token of [
    'displayed_columns_absent',
    'displayed_table_absent',
    'displayed_layout_unsupported',
    'statement_role_not_consolidated',
    'A35-W1',
  ]) {
    assert.equal(html.includes(token), false, 'leaked ' + token);
  }
  assert.equal(nodes['ff-statements'].getAttribute('title'), null);
});

test('A35-W1 resolves through PEER_EXCLUSIONS in both languages', () => {
  const { api } = harness();
  const copy = api.peerExclusionCopy('A35-W1');
  assert.match(copy.en, /Statement not rebuilt from this filing/);
  assert.match(copy.zh, /未能从该财报重建此报表/);
});

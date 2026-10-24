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

// Refusal entries use the kernel's R-B2 shape (statement_graph.reconstruct_primary_statements):
// identity fields, empty columns/rows, row_count 0, and refusal carrying the code only.
const RAW_ROLE_URI = 'http://filer.example/role/RawConsolidatedBalanceSheet';
const RAW_TITLE = 'RAW FILER TITLE 0000070858';
const STRAY_MESSAGE = 'kernel diagnostic detail text';

function refusalEntry(statement_type, code, { nullIdentity = false } = {}) {
  return {
    statement_type,
    role_uri: nullIdentity ? null : RAW_ROLE_URI,
    title: nullIdentity ? null : RAW_TITLE,
    columns: [],
    row_count: 0,
    rows: [],
    refusal: { code },
  };
}

function mixedStatements() {
  const withheld = refusalEntry('balance_sheet', 'displayed_columns_absent');
  // Defensive: generation bytes never carry a message, and the desk must not render one if it appears.
  withheld.refusal.message = STRAY_MESSAGE;
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
    withheld,
  ];
}

function allRefusedStatements() {
  return [
    refusalEntry('income_statement', 'statement_role_not_consolidated', { nullIdentity: true }),
    refusalEntry('balance_sheet', 'displayed_columns_absent'),
    refusalEntry('cash_flow', 'displayed_columns_absent'),
  ];
}

function titleAttributes(html) {
  return [...html.matchAll(/\btitle\s*=\s*("([^"]*)"|'([^']*)')/g)].map((match) => match[2] ?? match[3] ?? '');
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

for (const [name, statements] of [['mixed', mixedStatements], ['all-refused', allRefusedStatements]]) {
  test(`refusal code, message, slug and raw identity never appear in rendered HTML (${name})`, () => {
    const { api, nodes } = harness();
    api.state.statements = { phase: 'ready', statements: statements() };
    api.renderStatementTree();
    const html = nodes['ff-statements'].innerHTML;
    for (const token of [
      'displayed_columns_absent',
      'displayed_table_absent',
      'displayed_layout_unsupported',
      'statement_role_not_consolidated',
      'A35-W1',
      RAW_ROLE_URI,
      RAW_TITLE,
      STRAY_MESSAGE,
    ]) {
      assert.equal(html.includes(token), false, 'leaked ' + token);
    }
    assert.equal(nodes['ff-statements'].getAttribute('title'), null);
    for (const value of titleAttributes(html)) {
      for (const fragment of ['rebuild this statement', 'rebuild this filing', '逐行重建', 'displayed_', 'statement_role_']) {
        assert.equal(value.includes(fragment), false, 'title attribute carries ' + fragment);
      }
    }
  });
}

test('A35-W1 resolves through PEER_EXCLUSIONS in both languages', () => {
  const { api } = harness();
  const copy = api.peerExclusionCopy('A35-W1');
  assert.match(copy.en, /Statement not rebuilt from this filing/);
  assert.match(copy.zh, /未能从该财报重建此报表/);
});

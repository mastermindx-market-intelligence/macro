// A19 — hostile source bytes stay inert in the workbench.
//
// Two halves. The static half reads templates/fundamental_forensics.js as text
// and pins the sink rules: no script-evaluating sinks, esc() covers the five
// HTML metacharacters, and every interpolated href is a variable bound from a
// vetted URL helper that admits only http(s). The runtime half pushes markup,
// attribute-breakout and script payloads through every source-derived field
// of the statement tree, the normalized table, the evidence drawer and the
// revisions table, and requires each rendered tag to carry no payload tag or
// event-handler attribute while the escaped payload is still shown.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const PAGE_SOURCE = readFileSync(new URL('../templates/fundamental_forensics.js', import.meta.url), 'utf8');

const XSS = '<img src=x onerror="globalThis.__pwned=1">';
const BREAKOUT = '"><svg onload=alert(1)>';
const SCRIPT = '</code></td><script>globalThis.__pwned=1</script>';
const PAYLOAD = XSS + BREAKOUT + SCRIPT + "'&";

function escText(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Escaped text never carries a raw '<' or '>', and esc() turns '"' into
// &quot;, so after dropping double-quoted attribute values every remaining
// <...> run is a real tag the renderer emitted. A breakout would surface as an
// injected tag name or an on* attribute inside one of those runs.
function assertInert(html, where) {
  assert.equal(typeof html, 'string', where + ': no html rendered');
  const residue = html.replace(/="[^"]*"/g, '=""');
  const tags = residue.match(/<[^<>]*>/g) || [];
  assert.ok(tags.length > 0, where + ': rendered no markup');
  for (const tag of tags) {
    assert.doesNotMatch(tag, /^<\/?\s*(img|svg|script|iframe|object|embed)\b/i, where + ': injected tag ' + tag);
    assert.doesNotMatch(tag, /\son[a-z]+\s*=/i, where + ': event handler in ' + tag);
  }
  assert.equal(html.includes(XSS), false, where + ': raw markup payload');
  assert.equal(html.includes(BREAKOUT), false, where + ': raw breakout payload');
  assert.equal(html.includes('<script'), false, where + ': raw script tag');
}

function element() {
  const classes = new Set();
  const attrs = {};
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
  const nodes = {
    'ff-statements': element(),
    'ff-evidence': element(),
    'ff-evidence-body': element(),
    'ff-evidence-title': element(),
    'ff-revisions-table': element(),
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
  api.state.payload = {
    companies: {
      AAPL: {
        symbol: 'AAPL',
        entity_id: 'ISS:US-XNAS-AAPL',
        periods: [{ fiscal_year: PAYLOAD, fiscal_quarter: PAYLOAD, period_end: PAYLOAD, filed: PAYLOAD, revenue: PAYLOAD }],
      },
    },
    default_symbol: 'AAPL',
  };
  api.state.symbol = 'AAPL';
  return { api, nodes };
}

function hostileQueryNode(metricId) {
  return {
    cell_id: PAYLOAD,
    metric_id: metricId,
    value: PAYLOAD,
    unit: PAYLOAD,
    snapshot_id: PAYLOAD,
    display_excerpt: PAYLOAD,
    provenance: {
      accession: PAYLOAD,
      selected_raw_fact: { occurrence_id: PAYLOAD, source_span: [12, 48] },
    },
  };
}

function hostileControl(overrides) {
  const values = Object.assign({
    'data-source-kind': PAYLOAD,
    'data-occurrence-id': PAYLOAD,
    'data-root-cell-id': PAYLOAD,
    'data-snapshot-id': PAYLOAD,
    'data-accession': PAYLOAD,
    'data-span-start': PAYLOAD,
    'data-span-end': PAYLOAD,
  }, overrides || {});
  return {
    disabled: false,
    getAttribute: (key) => (Object.prototype.hasOwnProperty.call(values, key) ? values[key] : null),
    querySelector: (selector) => (selector === '.ff-compact' ? { textContent: PAYLOAD } : null),
  };
}

// ── static half ─────────────────────────────────────────────────────────────

test('no script-evaluating sink exists in the workbench source', () => {
  for (const [name, pattern] of [
    ['document.write', /document\.write/],
    ['eval', /\beval\s*\(/],
    ['new Function', /new\s+Function\s*\(/],
    ['outerHTML', /outerHTML/],
    ['srcdoc', /srcdoc/i],
    ['javascript: url', /javascript:/i],
    ['inline handler in markup', /<[a-z][^'"<>]*\son[a-z]+\s*=/i],
    ['setTimeout with a string', /setTimeout\s*\(\s*['"]/],
  ]) {
    assert.doesNotMatch(PAGE_SOURCE, pattern, 'forbidden sink: ' + name);
  }
});

test('esc() escapes all five HTML metacharacters', () => {
  const start = PAGE_SOURCE.indexOf('function esc(value) {');
  assert.ok(start >= 0, 'esc() is defined');
  const end = PAGE_SOURCE.indexOf('\n  }\n', start);
  const esc = vm.runInNewContext('(' + PAGE_SOURCE.slice(start, end + 4) + ')');
  assert.equal(esc(`<a href="x" title='y'>&</a>`), '&lt;a href=&quot;x&quot; title=&#39;y&#39;&gt;&amp;&lt;/a&gt;');
  assert.equal(esc(null), '');
  assert.equal(esc(PAYLOAD), escText(PAYLOAD));
});

const URL_HELPERS = ['safeUrl', 'documentSourceUrl', 'receiptUrl', 'companyFactsUrl'];

test('every vetted URL helper returns through safeUrl, which admits only http(s)', () => {
  const safe = PAGE_SOURCE.indexOf('function safeUrl(value) {');
  assert.ok(safe >= 0, 'safeUrl() is defined');
  const safeBody = PAGE_SOURCE.slice(safe, PAGE_SOURCE.indexOf('\n  }\n', safe));
  assert.match(safeBody, /parsed\.protocol === 'http:' \|\| parsed\.protocol === 'https:' \? parsed\.href : ''/);
  for (const helper of URL_HELPERS.slice(1)) {
    const at = PAGE_SOURCE.indexOf('function ' + helper + '(');
    assert.ok(at >= 0, helper + ' is defined');
    const body = PAGE_SOURCE.slice(at, PAGE_SOURCE.indexOf('\n  }\n', at));
    const returns = body.match(/return [^;]+;/g) || [];
    assert.ok(returns.length > 0, helper + ' returns');
    for (const statement of returns) {
      assert.ok(statement === "return '';" || statement.startsWith('return safeUrl('), helper + ' returns outside safeUrl: ' + statement);
    }
  }
});

test('every interpolated href is an escaped variable bound from a vetted URL helper', () => {
  const lines = PAGE_SOURCE.split('\n');
  let seen = 0;
  lines.forEach((line, index) => {
    for (const match of line.matchAll(/href="'\s*\+\s*([^+]+?)\s*\+/g)) {
      seen += 1;
      const inner = /^esc\(([A-Za-z_$][\w$]*)\)$/.exec(match[1].trim());
      assert.ok(inner, `line ${index + 1}: href interpolation is not esc(<variable>): ${match[1]}`);
      const name = inner[1];
      let binding = null;
      for (let back = index; back >= 0 && back > index - 120; back -= 1) {
        const declared = new RegExp('\\bvar ' + name + '\\s*=\\s*([^;]+);').exec(lines[back]);
        if (declared) { binding = declared[1].trim(); break; }
      }
      assert.ok(binding, `line ${index + 1}: no binding found for ${name}`);
      assert.ok(URL_HELPERS.some((helper) => binding.startsWith(helper + '(')),
        `line ${index + 1}: ${name} is bound from ${binding}, not a vetted URL helper`);
    }
  });
  assert.ok(seen >= 6, 'the href census found ' + seen + ' interpolations');
});

// ── runtime half ────────────────────────────────────────────────────────────

test('statement tree: hostile titles, labels, units and receipts render as text', () => {
  const { api, nodes } = harness();
  api.state.statements = {
    phase: 'ready',
    statements: [
      {
        statement_type: 'income_statement',
        title: PAYLOAD,
        columns: [{ label: PAYLOAD, start: '2023-10-01', end: '2024-09-28' }],
        rows: [{
          as_reported_label: PAYLOAD,
          standardized_metric_id: PAYLOAD,
          cells: [{
            quality_state: 'available',
            value: '100',
            unit: PAYLOAD,
            source_receipt: {
              occurrence_id: PAYLOAD,
              root_cell_id: PAYLOAD,
              snapshot_id: PAYLOAD,
              accession: PAYLOAD,
              source_span: [1, 5],
            },
          }],
        }],
      },
      { statement_type: PAYLOAD, title: PAYLOAD, columns: [], rows: [], row_count: 0, refusal: { code: PAYLOAD } },
    ],
  };
  api.renderStatementTree();
  const html = nodes['ff-statements'].innerHTML;
  assertInert(html, 'statement tree');
  assert.ok(html.includes('<h3>' + escText(PAYLOAD) + '</h3>'), 'the hostile title is shown escaped');
  assert.ok(html.includes('data-occurrence-id="' + escText(PAYLOAD) + '"'), 'the hostile receipt id is an escaped attribute');
  assert.ok(html.includes('class="ff-statement-label">' + escText(PAYLOAD) + '</td>'), 'the hostile label is shown escaped');
  // The tree cell resolves its drawer title from the as-reported label.
  const cell = api.cellEvidenceFromControl(hostileControl({ 'data-span-start': '1', 'data-span-end': '5' }));
  api.renderCellEvidence(cell);
  assertInert(nodes['ff-evidence-title'].innerHTML, 'statement-cell drawer title');
  assert.ok(nodes['ff-evidence-title'].innerHTML.includes(escText(PAYLOAD)), 'the drawer title shows the escaped label');
  assertInert(nodes['ff-evidence-body'].innerHTML, 'statement-cell drawer body');
});

test('normalized table: hostile period fields render as text', () => {
  const { api, nodes } = harness();
  api.state.statements = { phase: 'idle' };
  api.renderStatementTree();
  assertInert(nodes['ff-statements'].innerHTML, 'normalized table');
});

test('evidence drawer: hostile query node, control ids and vintages render as text', () => {
  const { api, nodes } = harness();
  api.state.queryNodes = [hostileQueryNode(PAYLOAD)];
  api.state.financial = {
    phase: 'ready',
    revisions: [{ metric_id: PAYLOAD, root_value: PAYLOAD, prior_value: PAYLOAD, revised_value: PAYLOAD }],
  };
  const cell = api.cellEvidenceFromControl(hostileControl());
  assert.equal(cell.exactText, PAYLOAD);
  api.renderCellEvidence(cell);
  const body = nodes['ff-evidence-body'].innerHTML;
  assertInert(body, 'drawer body');
  assertInert(nodes['ff-evidence-title'].innerHTML, 'drawer title');
  assert.ok(body.includes('<code class="ff-exact">' + escText(PAYLOAD) + '</code>'), 'the exact value is shown escaped');
  assert.ok(body.includes('<blockquote class="ff-span-excerpt">' + escText(PAYLOAD) + '</blockquote>'), 'the excerpt is shown escaped');
  assert.ok(body.includes('title="' + escText(PAYLOAD) + '"'), 'the occurrence id is an escaped title');
});

test('revisions table: hostile vintages, ids and policy echo render as text', () => {
  const { api, nodes } = harness();
  const node = hostileQueryNode('revenue');
  node.value = '94936000000';
  api.state.financial = {
    phase: 'ready',
    asReported: [node],
    latest: [node],
    restated: [node],
    revisions: [{ metric_id: 'revenue', root_value: PAYLOAD, prior_value: PAYLOAD, revised_value: '1' }],
    receiptPolicy: { source_snapshot_at: PAYLOAD, selection: PAYLOAD },
  };
  api.renderRevisions();
  const html = nodes['ff-revisions-table'].innerHTML;
  assertInert(html, 'revisions table');
  assert.ok(html.includes('data-accession="' + escText(PAYLOAD) + '"'), 'the hostile accession is an escaped attribute');
  assert.ok(html.includes(escText(PAYLOAD)), 'the hostile policy echo is shown escaped');
});

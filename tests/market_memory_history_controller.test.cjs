'use strict';
// Whole shipped controller, real gzip/SHA, a deliberately minimal DOM adapter.
// These are async controller unit tests, not visual or browser qualification.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { gzipSync } = require('node:zlib');
const { webcrypto, createHash } = require('node:crypto');
const source = fs.readFileSync(path.join(__dirname, '../templates/market_memory_history.js'), 'utf8');
class Element {
  constructor() { this.value = ''; this.hidden = true; this.disabled = false; this.dataset = {}; this.children = []; this.listeners = {}; this.textContent = ''; }
  append(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  setAttribute() {}
  get rows() { return this.children; }
  get options() { return this.children; }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  change(value) { this.value = value; this.listeners.change(); }
  click() { if (!this.disabled) return this.listeners.click(); }
}
const dates = ['2020-01-02', '2020-01-03'];
const symbols = ['SPY', 'QQQ'];
function payload(outcomes = false) {
  const columns = ['market_date', 'vendor_symbol', outcomes ? 'forward_return_1ob_pct' : 'return_1ob_pct'];
  return { mode: 'RETROSPECTIVE_EXPLORATORY', manifest_sha256: 'synthetic-only', columns,
    rows: dates.flatMap(d => symbols.map(s => [d, s, 1])),
    metadata: { coverage: { selected_proxy_count: 2, first_observed_date: dates[0], last_observed_date: dates[1], observed_dates: 2 },
      request: { benchmark: 'SPY', start: dates[0], end: dates[1], capture_cutoff: 'fixture', symbols: symbols.map(vendor_symbol => ({vendor_symbol})) }, basis: 'fixture', sources: [] } };
}
async function until(predicate) {
  for (let n = 0; n < 100; n++) { if (predicate()) return; await new Promise(r => setTimeout(r, 5)); }
  assert.fail('controller did not reach expected async boundary');
}
async function setup(kind = 'valid') {
  const nodes = new Map();
  const get = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  for (const id of ['mmh-table', 'mmh-outcomes-table']) get(id).tBodies = [new Element()];
  get('mmh-symbol').append(new Element());
  const outcomes = payload(true);
  if (kind === 'manifest') outcomes.manifest_sha256 = 'other-fixture';
  if (kind === 'index') outcomes.rows[0] = [dates[0], 'SPY'];
  for (const [id, data] of [['mmh-data', payload()], ['mmh-outcomes-data', outcomes]]) {
    const bytes = Buffer.from(JSON.stringify(data));
    get(id).textContent = gzipSync(bytes).toString('base64');
    get(id).dataset.sha256 = createHash('sha256').update(bytes).digest('hex');
  }
  const absent = new Set(['mmh-macro-data', 'mmh-filings-data', 'mmh-transcripts-data']);
  const pending = [];
  const document = { documentElement: {dataset: {lang:'en', theme:'light'}},
    getElementById: id => absent.has(id) ? null : get(id), createElement: () => new Element() };
  const context = {document, Blob, DecompressionStream, TextDecoder, Uint8Array, atob,
    crypto: {subtle: {digest: async (...args) => {
      if (Buffer.from(args[1]).toString().includes('forward_return_1ob_pct')) {
        const corrupt = await new Promise(resolve => pending.push(resolve));
        if (corrupt) return new ArrayBuffer(32);
      }
      return webcrypto.subtle.digest(...args);
    }}}};
  context.window = context;
  vm.runInNewContext(source, context, {filename:'market_memory_history.js'});
  const status = () => context.__MM_HISTORY_VIEW__.status();
  await until(() => status().ready || status().error);
  assert.equal(status().error, null);
  get('mmh-symbol').change('SPY');
  return {get, status, pending, async reveal() {
    const count = pending.length;
    const completed = get('mmh-reveal').click();
    await until(() => pending.length > count);
    return {completed};
  }};
}
for (const action of ['symbol', 'date-aba', 'step-aba', 'language', 'theme', 'hide']) {
  test(`pending reveal: ${action}`, async () => {
    const h = await setup();
    const first = await h.reveal();
    if (action === 'symbol') h.get('mmh-symbol').change('QQQ');
    if (action === 'date-aba') { h.get('mmh-date').change(dates[0]); h.get('mmh-date').change(dates[1]); }
    if (action === 'step-aba') { h.get('mmh-prev').click(); h.get('mmh-next').click(); }
    if (action === 'language' || action === 'theme') h.get(`mmh-${action}`).click();
    let second;
    if (action === 'hide') second = await h.reveal();
    h.pending[0](false); await first.completed;
    if (second) { h.get('mmh-reveal').click(); h.pending[1](false); await second.completed; }
    assert.equal(h.get('mmh-outcomes').hidden, !['language', 'theme'].includes(action));
    assert.equal(h.status().error, null);
    // Cached valid data remains available only after a fresh explicit click.
    if (!['language', 'theme'].includes(action)) { await h.get('mmh-reveal').click(); assert.equal(h.get('mmh-outcomes').hidden, false); }
  });
}
for (const kind of ['manifest', 'index']) {
  test(`${kind} rejection cannot publish cache or reopen after language change`, async () => {
    const h = await setup(kind), first = await h.reveal();
    h.pending[0](false); await first.completed;
    const error = h.status().error;
    assert.ok(error); assert.equal(h.status().outcomesDecoded, false);
    h.get('mmh-language').click();
    assert.equal(h.get('mmh-reveal').disabled, true);
    await h.get('mmh-reveal').click();
    assert.equal(h.pending.length, 1); assert.equal(h.status().error, error);
    assert.equal(h.get('mmh-outcomes').hidden, true);
  });
}
for (const errorFirst of [true, false]) {
  test(`concurrent integrity failure, error first=${errorFirst}`, async () => {
    const h = await setup(), valid = await h.reveal(), invalid = await h.reveal();
    if (errorFirst) { h.pending[1](true); await invalid.completed; h.pending[0](false); await valid.completed; }
    else { h.pending[0](false); await valid.completed; h.pending[1](true); await invalid.completed; }
    assert.equal(h.status().error, 'Browser payload digest mismatch');
    assert.equal(h.status().outcomesVisible, false);
    assert.equal(h.get('mmh-outcomes').hidden, true);
    assert.equal(h.status().outcomesDecoded, !errorFirst);
    h.get('mmh-language').click(); assert.equal(h.get('mmh-reveal').disabled, true);
  });
}

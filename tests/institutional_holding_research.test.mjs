import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const api = require('../templates/institutional_holding_research.js');
const selection = () => ({ ...api.EXAMPLES.current });
function payload(sel = selection()) {
  return {
    schema: 'institutional_13f.authenticated_research_context.v1', persistence: 'none', state: 'AVAILABLE_UNQUALIFIED',
    authority: { can_gate: false, can_open_entry: false, can_originate: false, can_rank: false, can_size: false },
    semantic_bindings: {
      reporting_entity: { state: 'OWNER_VERIFIED', owner: 'engine.institutional_census', filer_cik: sel.filer_cik, accession: sel.accession, source_receipt_id: 'test-receipt' },
      security: { state: 'UNRESOLVED', canonical_security_id: null },
      economic_vehicle: { state: 'UNRESOLVED', vehicle_epoch_id: null, vehicle_class: null, manager_complex_id: null },
      strategy: { state: 'UNRESOLVED', decision_mode: null }
    },
    context: {
      schema: 'institutional_13f.reported_holding_accession_context.v1', owner: 'engine.institutional_census', authority: 'descriptive_context_only', financial_influence: false, k3e_admissible: false, state: 'AVAILABLE_UNQUALIFIED', valid: true, refusals: [],
      interpretation: { class: 'DELAYED_REPORTED_HOLDING_CONTEXT', is_current_ownership: false, is_flow: false, is_intent: false, is_conviction: false },
      qualification: { state: 'NOT_QUALIFIED', canonical_security_id: null, source_use: 'UNKNOWN' },
      filing: { filer_cik: sel.filer_cik, report_period: sel.report_period, accession: sel.accession, filer_name: 'Fixture reporting entity', source_receipt_id: 'test-receipt' },
      holding: { infotable_sk: sel.infotable_sk, name_of_issuer: '<img src=x onerror=alert(1)>', quantity: { value: '7', type: 'SH' } },
      generation: { generation_id: sel.generation_id, report_period: sel.report_period, current_generation_id: null, superseded: null, pointer: { state: 'not_read' }, validation_scope: { kind: 'accession_bucket', whole_generation_verified: false, verified_roles: ['filings_parquet', 'holdings_bucket_29_parquet', 'manager_relationships_parquet', 'source_receipts_json', 'coverage_json'] } }
    }
  };
}
function fixture(overrides = {}) {
  const events = [], requests = [];
  let current = null, busy = false;
  const controller = api.createController({
    AbortController,
    session: async () => ({ access_token: 'test-only-token' }),
    fetch: async (url, options) => { requests.push({ url, options }); return new Response(JSON.stringify(payload(JSON.parse(options.body))), { status: 200 }); },
    clear: () => { current = null; events.push('clear'); }, busy: value => { busy = value; },
    status: (kind, reasons) => events.push({ kind, reasons }), render: value => { current = value; events.push('render'); },
    ...overrides
  });
  return { controller, events, requests, current: () => current, busy: () => busy };
}
function deferred() { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; }

test('exact int64 text and original microsecond cutoff survive unchanged', () => {
  assert.deepEqual(api.normalizeSelection(selection()), selection());
  assert.equal(api.normalizeSelection({ ...selection(), infotable_sk: '9223372036854775807' }).infotable_sk, '9223372036854775807');
  assert.notEqual(Number(selection().infotable_sk).toString(), selection().infotable_sk);
});
for (const [field, value] of [
  ['infotable_sk', 4611686018427387905], ['infotable_sk', '01'], ['infotable_sk', '-1'], ['infotable_sk', '9223372036854775808'], ['infotable_sk', '1e3'],
  ['filer_cik', '1904423'], ['accession', 'https://example.com'], ['report_period', '2026-02-30'], ['report_period', '0000-01-01'],
  ['decision_cutoff', '2026-08-27T09:22:23'], ['decision_cutoff', '2026-08-27T09:22:23+08:00'], ['decision_cutoff', '2026-02-30T09:22:23Z'], ['generation_id', 'current']
]) test(`reject imprecise/invalid selection ${field}:${value}`, () => assert.throws(() => api.normalizeSelection({ ...selection(), [field]: value })));
test('optional generation omitted and extra resolver payload rejected', () => {
  assert.equal('generation_id' in api.normalizeSelection({ ...selection(), generation_id: '' }), false);
  assert.throws(() => api.normalizeSelection({ ...selection(), owner_payload: {} }));
});
test('March and June examples bind distinct accession/catalog while preserving original cutoff', () => {
  const a = api.EXAMPLES.previous, b = api.EXAMPLES.current;
  assert.notEqual(a.accession, b.accession); assert.notEqual(a.generation_id, b.generation_id);
  assert.equal(a.decision_cutoff, b.decision_cutoff);
  assert.equal(a.infotable_sk, b.infotable_sk);
});
test('native available context retains research ceiling and exact selection', () => assert.equal(api.validateResponse(payload(), selection()).state, 'AVAILABLE_UNQUALIFIED'));
for (const [name, mutate] of [
  ['promoted authority', p => { p.authority.can_size = true; }],
  ['additional authority', p => { p.authority.can_trade = true; }],
  ['positive K3E', p => { p.context.k3e_admissible = true; }],
  ['current ownership', p => { p.context.interpretation.is_current_ownership = true; }],
  ['canonical security', p => { p.semantic_bindings.security.canonical_security_id = 'invented'; }],
  ['economic vehicle', p => { p.semantic_bindings.economic_vehicle.vehicle_class = 'hedge_fund'; }],
  ['strategy', p => { p.semantic_bindings.strategy.decision_mode = 'discretionary'; }],
  ['wrong filing', p => { p.context.filing.accession = api.EXAMPLES.previous.accession; }],
  ['wrong row', p => { p.context.holding.infotable_sk = Number(selection().infotable_sk); }],
  ['wrong generation', p => { p.context.generation.generation_id = api.EXAMPLES.previous.generation_id; }],
  ['whole-generation claim', p => { p.context.generation.validation_scope.whole_generation_verified = true; }],
  ['unread supersession claim', p => { p.context.generation.superseded = false; }],
  ['reporting alias mismatch', p => { p.semantic_bindings.reporting_entity.filer_cik = '0000000001'; }]
]) test(`reject ${name}`, () => { const p = payload(); mutate(p); assert.throws(() => api.validateResponse(p, selection())); });
test('unavailable and refused remain typed non-absence conclusions', () => {
  for (const state of ['UNAVAILABLE', 'REFUSED']) {
    const p = payload(); p.state = p.context.state = state; p.context.valid = false; p.context.filing = p.context.holding = null; p.context.refusals = ['HOLDING_ROW_NOT_FOUND'];
    assert.equal(api.validateResponse(p, selection()).state, state);
  }
});
test('bounded response rejects oversized body and declared length', async () => {
  await assert.rejects(api.readBoundedJson(new Response(' '.repeat(65537))));
  await assert.rejects(api.readBoundedJson(new Response('{}', { headers: { 'content-length': '65537' } })));
});
test('read submits same-origin JSON, exact text and bearer header without token in URL/body', async () => {
  const f = fixture(); await f.controller.read(selection());
  assert.equal(f.requests.length, 1);
  const { url, options } = f.requests[0];
  assert.equal(url, '/api/forensics/v1/institutional/reported-holding');
  assert.equal(options.headers.Authorization, 'Bearer test-only-token');
  assert.equal(options.cache, 'no-store'); assert.equal(options.method, 'POST'); assert.equal(options.redirect, 'error');
  assert.deepEqual(JSON.parse(options.body), selection());
  assert.equal(url.includes('test-only-token') || options.body.includes('test-only-token'), false);
  assert.equal(f.current().state, 'AVAILABLE_UNQUALIFIED'); assert.equal(f.busy(), false);
});
test('signed-out read has no fetch and clears prior result', async () => {
  const f = fixture({ session: async () => null }); await f.controller.read(selection());
  assert.equal(f.requests.length, 0); assert.equal(f.current(), null); assert.equal(f.busy(), false);
  assert.equal(f.events.at(-1).kind, 'signin');
});
for (const [status, kind] of [[401, 'signin'], [403, 'denied'], [503, 'unavailable']]) test(`${status} leaves no private result`, async () => {
  const f = fixture({ fetch: async () => new Response('{"secret_backend_detail":"not exposed"}', { status }) });
  await f.controller.read(selection()); assert.equal(f.current(), null); assert.equal(f.events.at(-1).kind, kind);
  assert.equal(JSON.stringify(f.events).includes('secret_backend_detail'), false);
});
test('clear invalidates pending session before it can fetch', async () => {
  const d = deferred(), f = fixture({ session: () => d.promise });
  const pending = f.controller.read(selection()); assert.equal(f.busy(), true);
  f.controller.clear(); d.resolve({ access_token: 'late' }); await pending;
  assert.equal(f.requests.length, 0); assert.equal(f.current(), null); assert.equal(f.busy(), false);
});
test('changing selection clears immediately and late old response cannot replace newer result', async () => {
  const old = deferred(); let calls = 0;
  const f = fixture({ fetch: async (_url, options) => ++calls === 1 ? old.promise : new Response(JSON.stringify(payload(JSON.parse(options.body)))) });
  const a = f.controller.read(selection()); await Promise.resolve();
  f.controller.clear(); assert.equal(f.current(), null);
  await f.controller.read({ ...api.EXAMPLES.previous });
  assert.equal(f.current().context.filing.report_period, '2026-03-31');
  old.resolve(new Response(JSON.stringify(payload()))); await a;
  assert.equal(f.current().context.filing.report_period, '2026-03-31'); assert.equal(f.busy(), false);
});
test('auth loss during response decoding cannot expose the former account result', async () => {
  const body = deferred();
  const f = fixture({ fetch: async () => ({ ok: true, headers: new Headers(), text: () => body.promise }) });
  const reading = f.controller.read(selection()); await Promise.resolve(); await Promise.resolve();
  f.controller.clear(); body.resolve(JSON.stringify(payload())); await reading;
  assert.equal(f.current(), null); assert.equal(f.events.includes('render'), false);
});
test('hostile source text is emitted as text nodes, never parsed HTML', () => {
  class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.hidden = true; }
    appendChild(value) { this.children.push(value); } replaceChildren() { this.children = []; }
    set innerHTML(_) { throw new Error('HTML parsing forbidden'); }
  }
  const doc = { createElement: tag => new Element(tag) }, target = new Element('div');
  api.renderAvailable(doc, target, payload(), selection());
  const nodes = []; function walk(n) { nodes.push(n); n.children.forEach(walk); } walk(target);
  assert.equal(nodes.some(n => n.textContent === '<img src=x onerror=alert(1)>'), true);
  assert.equal(nodes.some(n => n.tag === 'img'), false);
  assert.equal(target.hidden, false);
  assert.equal(nodes.find(n => n.tag === 'a').href, 'https://www.sec.gov/Archives/edgar/data/1904423/000190442326000004/0001904423-26-000004-index.html');
});

test('mounted first-party reader awaits the native asynchronous MDXAuth client', async () => {
  const client = deferred(), requests = [];
  function element() { return { firstChild: null, hidden: false, disabled: false,
    appendChild() {}, removeChild() {}, replaceChildren() {}, setAttribute() {}, addEventListener() {},
    querySelectorAll() { return []; } }; }
  const nodes = new Map();
  const doc = { getElementById(id) { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); }, createElement: element };
  const controller = api.mount({ document: doc, AbortController, location: { hash: '' }, addEventListener() {},
    MDXAuth: { client: () => client.promise, onChange() {} },
    fetch: async (url, options) => { requests.push({url,options}); return new Response('', { status: 503 }); }
  });
  const reading = controller.read(selection());
  await Promise.resolve();
  assert.equal(requests.length, 0);
  client.resolve({ auth: { getSession: async () => ({ data: { session: { access_token: 'fixture-token' } }, error: null }) } });
  await reading;
  assert.equal(requests.length, 1);
  assert.equal(requests[0].options.headers.Authorization, 'Bearer fixture-token');
  assert.deepEqual(JSON.parse(requests[0].options.body), selection());
  assert.equal(nodes.get('ff-holding-read').disabled, false);
});

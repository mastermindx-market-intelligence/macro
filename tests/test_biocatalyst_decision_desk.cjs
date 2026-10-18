'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const desk = require('../templates/biocatalyst_decision_desk.js');
const fixtures = path.join(__dirname, '../research/catalyst_intelligence/decision_desk_r1/fixtures');
const read = name => JSON.parse(fs.readFileSync(path.join(fixtures, name), 'utf8'));
const copy = value => JSON.parse(JSON.stringify(value));
const baseline = read('company-page.json'), detail = read('company-detail.json');
const key = desk.rowKey(baseline.rows[0]);
function deferred() { let resolve, reject; const promise = new Promise((r, j) => { resolve = r; reject = j; }); return {promise, resolve, reject}; }
function controller(overrides = {}) {
  return desk.createController({loadPage: async () => copy(baseline), loadDetail: async () => copy(detail), getContextKey: () => 'test-account:context-1', ...overrides});
}
function pageWith(change) { const p = copy(baseline); change(p, p.rows[0]); return p; }

test('fixtures retain exact API response bytes and identify their synthetic/test-auth scope', () => {
  const receipt = read('capture-receipt.json');
  assert.equal(receipt.candidate_head, 'ec5c2e2544576f20348c6eadf834fe3cefae8039');
  assert.equal(receipt.entitled_runtime_verified, false); assert.equal(receipt.source_admission, false);
  for (const response of receipt.responses) {
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(fixtures, response.file))).digest('hex'), response.sha256);
    assert.equal(response.cache_control, 'private, no-store'); assert.equal(response.vary, 'Authorization');
  }
});
test('unaltered API page and detail validate; optional unavailable estimates keep the research task', async () => {
  const c = controller(); await c.refresh(); await c.open(key);
  assert.equal(c.getState().phase, 'loaded'); assert.equal(c.getState().detail.phase, 'loaded');
  assert.equal(c.getState().page.state, 'partial');
  assert.equal(desk.presentation(baseline.rows[0], baseline).restricted, false);
  assert.match(desk.presentation(baseline.rows[0], baseline).task, /Review the disclosed milestone/);
  assert.equal(desk.stockLinks(baseline.rows[0])[0].href, 'stock.html?ticker=AMLX');
});
test('refresh removes current page, detail and counts before the next response arrives', async () => {
  const pending = deferred(); let calls = 0;
  const c = controller({loadPage: () => ++calls === 1 ? copy(baseline) : pending.promise});
  await c.refresh(); await c.open(key); const refresh = c.refresh();
  assert.equal(c.getState().phase, 'loading'); assert.equal(c.getState().page, null); assert.equal(c.getState().detail, null);
  pending.resolve(copy(baseline)); await refresh;
});
test('late old list response cannot resurrect a cleared or newer page even if abort is ignored', async () => {
  const first = deferred(), second = deferred(); let calls = 0;
  const c = controller({loadPage: () => (++calls === 1 ? first : second).promise});
  const a = c.refresh(), b = c.refresh();
  second.resolve(pageWith(p => { p.generation_id = 'new-publication'; p.rows = []; p.pagination.total = 0; })); await b;
  first.resolve(copy(baseline)); await a;
  assert.equal(c.getState().page.generation_id, 'new-publication'); assert.equal(c.getState().page.rows.length, 0);
});
test('late old detail cannot restore a case after list refresh', async () => {
  const pending = deferred(); const c = controller({loadDetail: () => pending.promise});
  await c.refresh(); const open = c.open(key); await c.refresh(); pending.resolve(copy(detail)); await open;
  assert.equal(c.getState().detail, null); assert.equal(c.getState().selectedKey, null);
});
test('latest detail selection wins when an older request returns last', async () => {
  const first = deferred(), second = deferred(); let calls = 0;
  const c = controller({loadDetail: () => (++calls === 1 ? first : second).promise}); await c.refresh();
  const a = c.open(key), b = c.open(key); second.resolve(copy(detail)); await b;
  first.reject(Object.assign(new Error('old error'), {status: 409})); await a;
  assert.equal(c.getState().detail.phase, 'loaded');
});
for (const status of [400, 401, 402, 403, 404, 409, 500, 503]) {
  test(`HTTP ${status} clears previously displayed cases and estimates without demo fallback`, async () => {
    let fail = false;
    const c = controller({loadPage: async () => { if (fail) throw Object.assign(new Error('raw server detail'), {status}); return copy(baseline); }});
    await c.refresh(); fail = true; await c.refresh();
    assert.equal(c.getState().phase, 'unavailable'); assert.equal(c.getState().page, null);
    assert.equal(c.getState().detail, null); assert(!JSON.stringify(c.getState()).includes('raw server detail'));
  });
}
test('context change immediately clears visible data and rejects in-flight account response', async () => {
  const pending = deferred(); let account = 'A';
  const c = controller({getContextKey: () => account, loadPage: () => pending.promise});
  const request = c.refresh(); account = 'B'; c.contextChanged(); pending.resolve(copy(baseline)); await request;
  assert.equal(c.getState().page, null); assert.equal(c.getState().issue, 'CONTEXT_CHANGED');
});
test('context change discovered at completion clears response even without a host notification', async () => {
  const pending = deferred(); let account = 'A';
  const c = controller({getContextKey: () => account, loadPage: () => pending.promise});
  const request = c.refresh(); account = 'B'; pending.resolve(copy(baseline)); await request;
  assert.equal(c.getState().page, null); assert.equal(c.getState().issue, 'CONTEXT_CHANGED');
});
test('host context exceptions during a pending request fail closed', async () => {
  const pending = deferred(); let fail = false;
  const c = controller({getContextKey: () => { if (fail) throw new Error('session missing'); return 'A'; }, loadPage: () => pending.promise});
  const r = c.refresh(); fail = true; pending.resolve(copy(baseline)); await r;
  assert.equal(c.getState().page, null);
});
test('destroyed consumer cannot repaint on pending completion', async () => {
  const pending = deferred(); const c = controller({loadPage: () => pending.promise}); let notifications = 0;
  c.subscribe(() => notifications++); const r = c.refresh(); c.destroy(); const before = notifications;
  pending.resolve(copy(baseline)); await r; assert.equal(notifications, before); assert.equal(c.getState().page, null);
});
for (const [name, change] of [
  ['contract version', p => { p.schema_version = '1.1.0'; }],
  ['missing required evidence array', (p, r) => { delete r.evidence; }],
  ['trade authority', p => { p.authority.trade_origination = true; }],
  ['numeric forecast under unsupported schema', (p, r) => { r.probability.state = 'ESTIMATED'; r.probability.value = .73; }],
  ['future identity observation', (p, r) => { r.issuer.identity_observed_at = '2026-08-02T00:00:00Z'; }],
  ['future alias date', (p, r) => { r.issuer.securities[0].symbol_observed_on = '2026-08-02'; }],
  ['issuer key mismatch', (p, r) => { r.row_key.issuer_id = 'ISS:other'; }],
  ['revision summary mismatch', (p, r) => { r.revision_summary.revision_ref = 'other'; }],
  ['malformed date', (p, r) => { r.timing.lower_date = '2026-02-30'; }],
  ['wrong method', (p, r) => { r.research_priority.method_id = 'new-rank'; }],
  ['foreign query', p => { p.query.view = 'history'; }],
  ['duplicate rows', (p, r) => { p.rows.push(copy(r)); p.pagination.total = 2; }],
  ['incomplete page without cursor', p => { p.pagination.total = 3; }],
  ['empty envelope containing rows', p => { p.state = 'empty'; }]
]) test(`rejects ${name}`, async () => {
  const c = controller({loadPage: async () => pageWith(change)}); await c.refresh();
  assert.equal(c.getState().phase, 'unavailable'); assert.equal(c.getState().page, null);
});
for (const [name, change] of [
  ['publication', d => { d.generation_id = 'other'; }],
  ['issuer', d => { d.event.issuer.issuer_id = 'ISS:other'; d.event.row_key.issuer_id = 'ISS:other'; }],
  ['revision', d => { d.event.event_revision_ref = 'revised'; d.event.revision_summary.revision_ref = 'revised'; }],
  ['timing conflict', d => { d.event.timing.state = 'conflicted'; }],
  ['withdrawal', d => { d.event.occurrence = 'withdrawn'; }],
  ['security join', d => { d.event.issuer.securities[0].security_id = 'SEC:other'; }]
]) test(`detail ${name} mismatch clears all dependent list and detail content`, async () => {
  const d = copy(detail); change(d); const c = controller({loadDetail: async () => d});
  await c.refresh(); await c.open(key); assert.equal(c.getState().page, null); assert.equal(c.getState().detail, null);
});
test('pagination remains in one exact publication and preserves server ordering', async () => {
  const first = pageWith(p => { p.pagination.total = 2; p.pagination.next_cursor = 'cursor-1'; });
  const second = copy(first); second.pagination.next_cursor = null;
  second.rows[0].event_fact_ref = 'event-second'; second.rows[0].row_key.event_fact_ref = 'event-second';
  const c = controller({loadPage: async args => args.cursor ? second : first});
  await c.refresh(); await c.more();
  assert.equal(c.getState().page.rows.length, 2); assert.equal(c.getState().page.rows[0].event_fact_ref, baseline.rows[0].event_fact_ref);
});
for (const mode of ['generation', 'duplicate', 'cutoff', 'cursor-loop', 'coverage']) test(`pagination ${mode} inconsistency clears the page`, async () => {
  const first = pageWith(p => { p.pagination.total = 2; p.pagination.next_cursor = 'cursor-1'; });
  const second = copy(first); second.pagination.next_cursor = null;
  if (mode !== 'duplicate') { second.rows[0].event_fact_ref = 'event-second'; second.rows[0].row_key.event_fact_ref = 'event-second'; }
  if (mode === 'generation') second.generation_id = 'other';
  if (mode === 'cutoff') second.evaluation_cutoff = '2026-08-01T15:00:05Z';
  if (mode === 'cursor-loop') second.pagination.next_cursor = 'cursor-1';
  if (mode === 'coverage') second.coverage.missing_owner_ports = [];
  const c = controller({loadPage: async args => args.cursor ? second : first}); await c.refresh(); await c.more();
  assert.equal(c.getState().page, null);
});
test('conflicted, withdrawn, superseded and stale records suppress the earlier forward-looking title', () => {
  for (const change of [r => { r.timing.state = 'conflicted'; }, r => { r.occurrence = 'withdrawn'; },
    r => { r.revision_is_current = false; }, r => { r.missingness.source = ['SOURCE_NOT_CURRENT']; }]) {
    const p = copy(baseline); change(p.rows[0]); const view = desk.presentation(p.rows[0], p);
    assert(view.restricted); assert.notEqual(view.title, desk.presentation(baseline.rows[0], baseline).title);
  }
});
test('unresolved issuer is explicit and cannot acquire a guessed stock link', () => {
  const p = copy(baseline), r = p.rows[0];
  r.issuer = {state: 'unresolved', issuer_id: null, company_id: r.issuer.company_id, relationship_role: null,
    identity_scope: 'unavailable', identity_observed_at: null, securities: []};
  r.row_key.issuer_id = null; desk.validatePage(p);
  assert.equal(desk.stockLinks(r).length, 0); assert.equal(desk.presentation(r, p).symbol, 'Issuer unresolved');
});
test('a superseded version does not claim that the underlying event was withdrawn', () => {
  const p = copy(baseline), r = p.rows[0]; r.revision_is_current = false;
  const v = desk.presentation(r,p); assert.match(v.title, /version has been superseded/);
  assert.match(v.risk, /does not establish whether the event changed or ended/);
  assert(!/no longer an upcoming|resolved event history/.test(v.title+' '+v.task));
});
test('an elapsed uncorroborated window becomes an outcome-reconciliation task', () => {
  const p = copy(baseline); p.anchor_date='2026-10-01';
  const v=desk.presentation(p.rows[0],p); assert(v.restricted); assert.match(v.title,/Confirm whether the milestone occurred/);
});
test('stock navigation requires exact supplied security and symbol without parameters or URL fallback', () => {
  for (const href of ['https://example.test/stock.html?ticker=AMLX', '//example.test/', 'javascript:alert(1)',
    'stock.html?ticker=OTHER', 'stock.html?ticker=AMLX&next=evil', 'stock.html?ticker=%ZZ']) {
    const r = copy(baseline.rows[0]); r.links.stock_research[0].href = href; assert.equal(desk.stockLinks(r).length, 0);
  }
});
test('all supplied active share classes retain independent, correctly bound links', () => {
  const r = copy(baseline.rows[0]);
  r.issuer.securities.push({...r.issuer.securities[0], security_id: 'SEC:class-b', listing_key: 'US-XNAS-CLASSB', display_symbol: 'CLASS.B'});
  r.links.stock_research.push({security_id: 'SEC:class-b', relationship_role: 'issuer', href: 'stock.html?ticker=CLASS.B'});
  assert.deepEqual(desk.stockLinks(r).map(l => l.symbol), ['AMLX', 'CLASS.B']);
});
test('only an explicitly supplied registry source anchored to its timing reference is navigable', () => {
  const r = copy(baseline.rows[0]); r.event_family = 'registry_primary_completion';
  r.timing.evidence_refs = ['https://clinicaltrials.gov/study/NCT00000001'];
  r.evidence = [{url: r.timing.evidence_refs[0]}, {url: 'https://other.test/unrelated'}, {url: 'javascript:alert(1)'}];
  assert.deepEqual(desk.evidenceLinks(r), [{href: r.timing.evidence_refs[0], label: 'clinicaltrials.gov'}]);
  r.evidence = [{url: 'https://name:password@clinicaltrials.gov/study/NCT00000001'}]; assert.equal(desk.evidenceLinks(r).length, 0);
});
test('company evidence gap is honest; no URL is minted from its source reference', () => {
  assert.equal(desk.evidenceLinks(baseline.rows[0]).length, 0);
  const r = copy(baseline.rows[0]); r.evidence = [{url: 'https://example.test/claim'}];
  assert.equal(desk.evidenceLinks(r).length, 0, 'a new company evidence shape needs explicit admission');
});
test('accepted state is copied and immutable against subsequent host payload mutation', async () => {
  const p = copy(baseline); const c = controller({loadPage: async () => p}); await c.refresh();
  p.rows[0].timing.source_wording = 'changed behind the consumer';
  assert.equal(c.getState().page.rows[0].timing.source_wording, baseline.rows[0].timing.source_wording);
  assert.throws(() => { c.getState().page.rows.pop(); }, TypeError);
});

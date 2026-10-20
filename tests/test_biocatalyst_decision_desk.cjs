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

const sourceFixtures = path.join(fixtures, 'company_evidence_r2');
const sourceRead = name => JSON.parse(fs.readFileSync(path.join(sourceFixtures, name), 'utf8'));
const sourcePage = sourceRead('company-page.json'), sourceDetail = sourceRead('company-detail.json');
function sourceController(overrides = {}) {
  return controller({loadPage: async () => copy(sourcePage), loadDetail: async () => copy(sourceDetail), ...overrides});
}
test('new source context retains exact R2 API bytes, cut and explicitly synthetic scope', () => {
  const receipt = sourceRead('capture-receipt.json');
  assert.match(receipt.candidate_head, /^[0-9a-f]{40}$/);
  assert.notEqual(receipt.candidate_head, 'ec5c2e2544576f20348c6eadf834fe3cefae8039');
  assert.equal(receipt.source_admission, false); assert.equal(receipt.entitled_runtime_verified, false);
  for (const response of receipt.responses) {
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(sourceFixtures, response.file))).digest('hex'), response.sha256);
    assert.equal(response.cache_control, 'private, no-store'); assert.equal(response.vary, 'Authorization');
  }
  assert.equal(sourcePage.input_cut.cutoff, '2026-10-19T00:00:00Z');
  assert.equal(sourcePage.rows[0].evidence[0].excerpt, null);
});
test('unaltered R2 list and detail expose only the supplied source-context destination', async () => {
  const c = sourceController(); await c.refresh(); await c.open(desk.rowKey(sourcePage.rows[0]));
  assert.equal(c.getState().phase, 'loaded'); assert.equal(c.getState().detail.phase, 'loaded');
  const row = c.getState().page.rows[0], evidence = row.evidence[0];
  assert.deepEqual(desk.evidenceLinks(row), [{href: evidence.url, label: 'www.sec.gov', role: 'source_context'}]);
  assert.equal(desk.stockLinks(row)[0].href, 'stock.html?ticker=SYNB');
  assert.match(desk.presentation(row, sourcePage).risk, /Review whether the linked filing supports this milestone/);
  assert(!/confirmed|validated|buy|positive outcome/.test(desk.presentation(row, sourcePage).risk));
});
for (const [name, mutate] of [
  ['foreign event', (p, r, e) => { e.event_id = 'other-event'; }],
  ['noncanonical Company event', (p, r, e) => { e.event_id = r.event_fact_ref = r.row_key.event_fact_ref = 'evt_source_not_canonical'; }],
  ['Company source on a registry family', (p, r, e) => { r.event_family = 'registry_primary_completion'; }],
  ['lossy document revision', (p, r, e) => { e.document_revision = Number.MAX_SAFE_INTEGER + 1; }],
  ['duplicate document/span', (p, r, e) => { r.evidence.push(copy(e)); }],
  ['unbounded source list', (p, r, e) => { r.evidence = Array.from({length:129}, (_,i) => ({...copy(e), span_ref:'span_'+i.toString(16).padStart(20,'0')})); }],
  ['foreign revision', (p, r, e) => { e.event_revision_ref = 'other-revision'; }],
  ['foreign issuer', (p, r, e) => { e.issuer_cik = '0007654321'; }],
  ['malformed revision', (p, r, e) => { e.event_revision_ref = r.event_revision_ref = r.revision_summary.revision_ref = 'revision with spaces'; }],
  ['different SEC filing', (p, r, e) => { e.url = e.url.replace('000123456726000001', '000123456726000002'); }],
  ['different SEC issuer path', (p, r, e) => { e.url = e.url.replace('/1234567/', '/7654321/'); }],
  ['unsupported domain', (p, r, e) => { e.url = e.url.replace('www.sec.gov', 'example.test'); }],
  ['unbound query', (p, r, e) => { e.url += '?other=1'; }],
  ['non-public rights', (p, r, e) => { e.rights_state = 'licensed'; }],
  ['different rights profile', (p, r, e) => { e.rights_profile = 'rp_internal'; }],
  ['source-support promotion', (p, r, e) => { e.role = 'supports'; }],
  ['decision promotion', (p, r, e) => { e.authority.decision_authority = true; }],
  ['extra authority field', (p, r, e) => { e.authority.forecast = true; }],
  ['unapproved excerpt', (p, r, e) => { e.excerpt = 'a source passage'; }],
  ['private extension', (p, r, e) => { e.source_locator = '/private/source'; }],
  ['span outside document', (p, r, e) => { e.span_end_byte = e.document_bytes + 1; }],
  ['non-integer revision', (p, r, e) => { e.document_revision = true; }],
  ['coerced accession', (p, r, e) => { e.accession = ['0001234567-26-000001']; }],
  ['unsupported evidence version', (p, r, e) => { e.schema_version = '2.0.0'; }],
  ['availability after observation', (p, r, e) => { e.source_available_at = '2026-10-18T16:01:00.000001Z'; }],
  ['microsecond beyond input cut', (p, r, e) => { e.projection_cutoff = '2026-10-19T00:00:00.000001Z'; }],
  ['excess fractional precision', (p, r, e) => { e.observed_at = '2026-10-18T16:01:00.0000001Z'; }],
  ['normalized midnight', (p, r, e) => { e.observed_at = '2026-10-18T24:00:00Z'; }],
  ['year-zero availability', (p, r, e) => { e.source_available_at = '0000-01-01T00:00:00Z'; }],
  ['year-zero filing', (p, r, e) => { e.filed_on = '0000-01-01'; }],
  ['filing after projection', (p, r, e) => { e.filed_on = '2026-10-20'; }],
]) test('source context refuses ' + name + ' without retaining earlier visible data', async () => {
  const p = copy(sourcePage), row = p.rows[0]; mutate(p, row, row.evidence[0]);
  let invalid = false;
  const c = sourceController({loadPage: async () => invalid ? p : copy(sourcePage)});
  await c.refresh(); await c.open(desk.rowKey(sourcePage.rows[0]));
  invalid = true; await c.refresh();
  assert.equal(c.getState().phase, 'unavailable'); assert.equal(c.getState().page, null); assert.equal(c.getState().detail, null);
});
test('source projection at the exact microsecond cut is accepted without millisecond rounding', async () => {
  const p = copy(sourcePage), e = p.rows[0].evidence[0];
  p.input_cut.cutoff = p.evaluation_cutoff = e.projection_cutoff = '2026-10-19T00:00:00.000001Z';
  const c = sourceController({loadPage: async () => p}); await c.refresh();
  assert.equal(c.getState().phase, 'loaded');
});
test('detail cannot substitute another source inside the same publication and event revision', async () => {
  const d = copy(sourceDetail); d.event.evidence[0].url = d.event.evidence[0].url.replace('synthetic.htm', 'another.htm');
  const c = sourceController({loadDetail: async () => d}); await c.refresh(); await c.open(desk.rowKey(sourcePage.rows[0]));
  assert.equal(c.getState().page, null); assert.equal(c.getState().detail, null);
});
test('a source context link never removes correction or stale-record restrictions', () => {
  for (const change of [r => { r.occurrence = 'withdrawn'; }, r => { r.revision_is_current = false; },
    r => { r.timing.state = 'conflicted'; }, r => { r.missingness.source = ['SOURCE_NOT_CURRENT']; }]) {
    const p = copy(sourcePage); change(p.rows[0]);
    const v = desk.presentation(p.rows[0], p);
    assert.equal(v.restricted, true);
    assert.notEqual(v.risk, desk.presentation(sourcePage.rows[0], sourcePage).risk);
  }
});


// This is current R10 owner wire produced by its actual handlers from synthetic
// inputs. Disk admission/final publication checks and real entitlement are NOT
// asserted by this capture; those stay with the native owner and release gates.
const currentOwnerFolder = path.join(fixtures, 'company_evidence_r10');
const currentOwnerRead = name => JSON.parse(fs.readFileSync(path.join(currentOwnerFolder, name), 'utf8'));
const currentOwnerPage = currentOwnerRead('company-page.json');
const currentOwnerDetail = currentOwnerRead('company-detail.json');
function currentOwnerController(overrides = {}) {
  return desk.createController({loadPage: async () => copy(currentOwnerPage),
    loadDetail: async () => copy(currentOwnerDetail), getContextKey: () => 'synthetic-r10-account', ...overrides});
}
test('current R10 owner capture retains exact source identity, headers and all nine response bodies', () => {
  const receipt = currentOwnerRead('capture-receipt.json');
  assert.equal(receipt.candidate_head, '902465f702a30abb943b08e792d670827a68650b');
  assert.equal(receipt.historical_fixture_head, '430234957531693b6b13f026a161e28542086a82');
  for (const field of ['source_admission', 'entitled_runtime_verified', 'production_publication_verified',
    'native_admission_verified', 'final_disk_publication_recheck_verified']) assert.equal(receipt[field], false);
  assert.equal(receipt.owner_checkout_unchanged, true);
  assert.equal(receipt.bytecode_writes_disabled, true);
  assert.match(receipt.harness_limit, /handler\/composer wire proof only/);
  assert.equal(receipt.responses.length, 9);
  assert.equal(new Set(receipt.responses.map(r => r.file)).size, 9);
  for (const r of receipt.responses) {
    const bytes = fs.readFileSync(path.join(currentOwnerFolder, r.file));
    assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), r.sha256);
    assert.equal(r.status, 200); assert.equal(r.cache_control, 'private, no-store');
    assert.equal(r.vary, 'Authorization');
    if (r.file !== 'company-detail.json') {
      const page = JSON.parse(bytes);
      assert.equal(desk.validatePage(page, page.query), page);
    }
  }
  assert.equal(desk.checkDetail(currentOwnerDetail, currentOwnerPage, currentOwnerPage.rows[0]), currentOwnerDetail);
});
test('current owner alias-cut member survives consumption without inventing admission or forecast values', async () => {
  const c = currentOwnerController(); await c.refresh();
  await c.open(desk.rowKey(currentOwnerPage.rows[0]));
  assert.equal(c.getState().phase, 'loaded');
  assert.equal(c.getState().detail.phase, 'loaded');
  assert.deepEqual(c.getState().page.input_cut.members.map(m => m.contract_id), [
    'company_catalyst_event.v1', 'dataos_issuer_master.current', 'dataos_vendor_aliases.current']);
  assert.equal(c.getState().page.input_cut.members[2].sha256,
    '3bb2ce8202897aba57fcb3c599c7a0c240732ac32fb135b1c9b247d245269df5');
  for (const k of ['probability', 'materiality', 'historical_response', 'incorporation']) {
    assert.equal(c.getState().detail.payload.event[k].state, 'NOT_ESTIMABLE');
    assert.equal(c.getState().detail.payload.event[k].value, null);
  }
  assert.equal(c.getState().detail.payload.event.evidence[0].excerpt, null);
  assert.equal(desk.evidenceLinks(currentOwnerPage.rows[0])[0].role, 'source_context');
  c.destroy();
});
test('current owner wrong-generation detail clears the selected case rather than blending revisions', async () => {
  const altered = copy(currentOwnerDetail); altered.generation_id += '_later';
  const c = currentOwnerController({loadDetail: async () => altered});
  await c.refresh(); await c.open(desk.rowKey(currentOwnerPage.rows[0]));
  assert.equal(c.getState().page, null); assert.equal(c.getState().detail, null);
  assert.equal(c.getState().issue, 'RELOAD_REQUIRED'); c.destroy();
});
test('current owner source revision mismatch clears the selected case within the same generation', async () => {
  const altered = copy(currentOwnerDetail); altered.event.event_revision_ref += ':changed';
  altered.event.revision_summary.revision_ref = altered.event.event_revision_ref;
  const c = currentOwnerController({loadDetail: async () => altered});
  await c.refresh(); await c.open(desk.rowKey(currentOwnerPage.rows[0]));
  assert.equal(c.getState().phase, 'unavailable');
  assert.equal(c.getState().page, null); assert.equal(c.getState().detail, null); c.destroy();
});

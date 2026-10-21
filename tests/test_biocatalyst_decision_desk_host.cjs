'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const desk = require('../templates/biocatalyst_decision_desk.js');
const hostPath = path.join(__dirname, '../templates/biocatalyst_decision_desk_host.js');
const host = fs.existsSync(hostPath) ? require(hostPath) : {};
const fixtureRoot = path.join(__dirname, '../research/catalyst_intelligence/decision_desk_r1/fixtures');
const page = JSON.parse(fs.readFileSync(path.join(fixtureRoot, 'company-page.json')));
const detail = JSON.parse(fs.readFileSync(path.join(fixtureRoot, 'company-detail.json')));
const copy = x => JSON.parse(JSON.stringify(x));
const tick = () => new Promise(resolve => setImmediate(resolve));
function deferred() { let resolve; const promise = new Promise(r => { resolve = r; }); return {resolve, promise}; }
function rig({url = 'https://example.test/biocatalyst.html?mode=changes&unrelated=keep', fetchJson, initialUser = {id: 'account-a'}} = {}) {
  assert.equal(typeof host.mount, 'function', 'the Decision Desk host adapter must exist');
  const win = new EventTarget(), doc = new EventTarget(), calls = [], history = [], created = [];
  let user = initialUser;
  win.document = doc; doc.documentElement = {dataset: {lang: 'en'}};
  win.location = new URL(url);
  win.history = {state: {existing: true}, replaceState(state, _, href) { history.push(['replace', href]); win.location = new URL(href, win.location); },
    pushState(state, _, href) { history.push(['push', href]); win.location = new URL(href, win.location); }};
  win.MDXAuth = {user: () => user};
  const createDesk = options => {
    // Real contract/lifecycle controller; DOM painting is exercised separately in browser proof.
    const c = desk.createController(options);
    c.openCase = selection => { const key = JSON.stringify([selection.event_fact_ref, selection.issuer_id]);
      if (!c.getState().page?.rows.some(row => desk.rowKey(row) === key)) return false;
      c.open(key); return true; };
    created.push({c, options}); return c;
  };
  const adapter = host.mount({root: {}, window: win, createDesk,
    fetchJson: (href, signal) => { calls.push({href, signal}); if (fetchJson) return fetchJson(href, signal);
      const u = new URL(href, win.location);
      if (u.pathname.endsWith('/detail')) return copy(detail);
      const value = copy(page); value.query.view = u.searchParams.get('view');
      value.query.horizon_days = u.searchParams.has('horizon_days') ? Number(u.searchParams.get('horizon_days')) : null;
      return value;
    }});
  function emit(type, properties = {}) { const e = new Event(type); Object.assign(e, properties); win.dispatchEvent(e); }
  return {adapter, win, doc, calls, history, created, emit, setUser(value) { user = value; },
    auth(value, event = 'SIGNED_OUT') { user = value; emit('mdx-auth', {detail: {user: value, event}}); }};
}
test('anonymous access action opens the existing sign-in owner without reading source data', async () => {
  const r = rig({initialUser: null}); await r.adapter.ready;
  const requested = []; r.win.MDXAuth.open = mode => requested.push(mode);
  const action = r.created[0].options.onRequestAccess;
  assert.equal(typeof action, 'function', 'host must supply a usable access action');
  action();
  assert.deepEqual(requested, ['signin']); assert.equal(r.calls.length, 0);
  assert.equal(r.adapter.getState().page, null); r.adapter.destroy();
  action(); assert.deepEqual(requested, ['signin'], 'disposed host cannot reopen sign-in');
});
test('signed-in access refusal links to existing same-origin plans without exporting the case', async () => {
  const r = rig({url: 'https://example.test/biocatalyst.html?bci_case=private-ref',
    fetchJson: () => { throw Object.assign(new Error('paid access required'), {status: 402}); }});
  await r.adapter.ready;
  const redirects = []; r.win.location.assign = href => redirects.push(href);
  const action = r.created[0].options.onRequestAccess;
  assert.equal(typeof action, 'function'); action();
  assert.deepEqual(redirects, ['https://example.test/plans.html']);
  assert.equal(r.calls.length, 1); assert.equal(r.adapter.getState().page, null);
  r.adapter.destroy();
});
test('an unavailable sign-in owner falls back to the existing plans route, not another auth client', async () => {
  const r = rig({initialUser: null}); await r.adapter.ready;
  const redirects = []; r.win.location.assign = href => redirects.push(href);
  const action = r.created[0].options.onRequestAccess;
  assert.equal(typeof action, 'function'); action();
  assert.deepEqual(redirects, ['https://example.test/plans.html']);
  assert.equal(r.calls.length, 0); r.adapter.destroy();
});
test('host uses the existing authenticated fetch and omits null owner query fields', async () => {
  const r = rig(); await r.adapter.ready;
  assert.equal(r.adapter.getState().phase, 'loaded');
  const u = new URL(r.calls[0].href, r.win.location);
  assert.equal(u.pathname, '/api/biocatalyst/v1/what-matters-next');
  assert.deepEqual([...u.searchParams.keys()].sort(), ['horizon_days', 'limit', 'view']);
  assert.equal(u.searchParams.get('horizon_days'), '90');
  assert.ok(r.calls[0].signal instanceof AbortSignal);
  assert.equal(r.win.location.searchParams.get('mode'), 'changes');
  assert.equal(r.win.location.searchParams.get('unrelated'), 'keep');
  r.adapter.destroy();
});
test('idle logout clears rendered owner data synchronously without making an anonymous source request', async () => {
  const r = rig(); await r.adapter.ready; const count = r.calls.length;
  r.auth(null);
  assert.equal(r.adapter.getState().page, null); assert.equal(r.adapter.getState().detail, null);
  await tick(); assert.equal(r.calls.length, count);
  assert.equal(r.adapter.getState().issue, 'ACCESS_REQUIRED'); r.adapter.destroy();
});
test('an old account response cannot repaint after the host auth event even when abort is ignored', async () => {
  const pending = deferred(); let count = 0;
  const r = rig({fetchJson: () => ++count === 1 ? pending.promise : copy(page)});
  r.auth({id: 'account-b'}, 'SIGNED_IN'); await tick();
  assert.equal(r.adapter.getState().phase, 'loaded');
  const stale = copy(page); stale.generation_id = 'stale-account-a'; pending.resolve(stale);
  await r.adapter.ready; await tick();
  assert.notEqual(r.adapter.getState().page?.generation_id, 'stale-account-a'); r.adapter.destroy();
});
test('initial anonymous context stays access-required and never reads the owner source', async () => {
  const r = rig({initialUser: null}); await r.adapter.ready; await tick();
  assert.equal(r.adapter.getState().page, null); assert.equal(r.calls.length, 0);
  await r.adapter.refresh(); assert.equal(r.calls.length, 0); r.adapter.destroy();
});
for (const status of [401, 402, 403, 409, 500, 503]) {
  test(`host preserves HTTP ${status} refusal and clears a previously loaded case`, async () => {
    let fail = false;
    const r = rig({fetchJson: () => { if (fail) throw Object.assign(new Error('bounded refusal'), {status}); return copy(page); }});
    await r.adapter.ready; fail = true; await r.adapter.refresh();
    assert.equal(r.adapter.getState().page, null); assert.equal(r.adapter.getState().detail, null);
    assert.equal(r.adapter.getState().issue, [401,402,403].includes(status) ? 'ACCESS_REQUIRED' : status === 409 ? 'RELOAD_REQUIRED' : 'UNAVAILABLE');
    r.adapter.destroy();
  });
}
test('a direct case URL restores only a row admitted by the loaded page and preserves host routing', async () => {
  const row = page.rows[0]; const params = new URLSearchParams({mode: 'screen', bci_case: row.event_fact_ref,
    bci_issuer: row.row_key.issuer_id, bci_task: 'sources'});
  const r = rig({url: 'https://example.test/biocatalyst.html?' + params}); await r.adapter.ready; await tick();
  assert.equal(r.adapter.getState().selectedKey, desk.rowKey(row));
  assert.equal(r.adapter.getState().detail.phase, 'loaded');
  const u = new URL(r.calls[1].href, r.win.location);
  assert.equal(u.searchParams.get('generation_id'), page.generation_id);
  assert.equal(u.searchParams.get('event_fact_ref'), row.event_fact_ref);
  assert.equal(r.win.location.searchParams.get('mode'), 'screen');
  assert.equal(r.history.filter(x => x[0] === 'push').length, 0); r.adapter.destroy();
});
test('popstate restores the requested case without adding another history entry', async () => {
  const r = rig(); await r.adapter.ready; const row = page.rows[0], before = r.history.length;
  r.win.location.searchParams.set('bci_case', row.event_fact_ref);
  r.win.location.searchParams.set('bci_issuer', row.row_key.issuer_id); r.emit('popstate'); await tick();
  assert.equal(r.adapter.getState().selectedKey, desk.rowKey(row)); assert.equal(r.history.length, before); r.adapter.destroy();
});
test('component filter changes update only the host-owned Decision Desk URL keys', async () => {
  const r = rig(); await r.adapter.ready;
  await r.created[0].c.refresh({view: 'reconcile', horizon_days: null});
  const u = new URL(r.calls.at(-1).href, r.win.location);
  assert.equal(u.searchParams.has('horizon_days'), false);
  assert.equal(r.win.location.searchParams.get('bci_view'), 'reconcile');
  assert.equal(r.win.location.searchParams.get('mode'), 'changes'); r.adapter.destroy();
});
for (const suffix of ['bci_case=a&bci_case=b', 'bci_task=unsafe', 'bci_view=upcoming&bci_days=999', 'bci_issuer=orphan']) {
  test(`invalid route ${suffix} refuses without fetching or replacing the host URL`, async () => {
    const r = rig({url: 'https://example.test/biocatalyst.html?' + suffix}); await r.adapter.ready;
    assert.equal(r.calls.length, 0); assert.equal(r.adapter.getState().page, null);
    assert.equal(r.history.length, 0); r.adapter.destroy();
  });
}
test('pagehide clears private case state and bfcache return revalidates through the same host', async () => {
  const r = rig(); await r.adapter.ready; const count = r.calls.length;
  r.emit('pagehide'); assert.equal(r.adapter.getState().page, null);
  r.emit('pageshow', {persisted: true}); await tick();
  assert.equal(r.calls.length, count + 1); assert.equal(r.adapter.getState().phase, 'loaded'); r.adapter.destroy();
});
test('language changes remount the presentation without retaining old account responses', async () => {
  const r = rig(); await r.adapter.ready; r.doc.documentElement.dataset.lang = 'zh';
  r.doc.dispatchEvent(new Event('langchange')); await tick();
  assert.equal(r.created.length, 2); assert.equal(r.created[1].options.locale, 'zh');
  assert.equal(r.adapter.getState().phase, 'loaded'); r.adapter.destroy();
});
test('destroy removes auth, route and page listeners and never restarts owner requests', async () => {
  const r = rig(); await r.adapter.ready; r.adapter.destroy(); const count = r.calls.length;
  r.auth({id: 'account-c'}, 'SIGNED_IN'); r.emit('popstate'); r.emit('pageshow', {persisted: true});
  r.doc.dispatchEvent(new Event('langchange')); await r.adapter.refresh(); await tick();
  assert.equal(r.calls.length, count); assert.equal(r.adapter.getState().page, null);
});

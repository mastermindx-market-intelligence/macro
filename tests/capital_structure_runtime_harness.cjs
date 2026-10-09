/* Run the real desk handlers without adding a package dependency to Macro CI.
 * node tests/capital_structure_runtime_harness.cjs [repository-root]
 * Optional native-DOM qualification: CS_DOM_MODE=jsdom NODE_PATH=<modules> ...
 * Both modes execute the same source, events, request races and assertions.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.argv[2] || path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'templates/capital_structure.js'), 'utf8');
const native = process.env.CS_DOM_MODE === 'jsdom';
const A = 'sec:cik:0000000001';
const B = 'sec:cik:0000000002';
const tick = () => new Promise(resolve => setImmediate(resolve));
async function flush() { for (let n = 0; n < 4; n++) await tick(); }
function issuer(id, ticker, name) {
  return { issuer_id: id, identity: { ticker, name, cik: id.split(':').pop(), aliases: [], observed_tickers: [ticker] },
    latest_observed_event: { form: 'S-3', lifecycle_state: 'filed', classification_state: 'classified', clocks: { sec_accepted_at: '2026-10-08T14:00:00Z', mastermind_observed_at: '2026-10-08T15:00:00Z' } },
    what_changed: [], coverage: { event_count: 1, classified_event_count: 1, review_count: 0 } };
}
const records = { [A]: issuer(A, 'AAAA', 'Issuer A'), [B]: issuer(B, 'BBBB', 'Issuer B') };
const envelope = { as_of: '2026-10-08T16:00:00Z', generated_at: '2026-10-08T16:00:00Z', coverage: { freshness: 'fresh', horizon_state: 'current', issuer_count: 2 } };
function bodyFor(url, options = {}) {
  const parsed = new URL(url, 'https://example.test');
  const p = decodeURIComponent(parsed.pathname);
  if (p.endsWith('/coverage')) return envelope;
  if (p.endsWith('/overview')) return { ...envelope, records: Object.values(records), page: { next_cursor: null } };
  if (p.endsWith('/resolve')) {
    const ticker = parsed.searchParams.get('ticker').trim().toUpperCase();
    return { ...envelope, query: { ticker }, issuer: records[ticker === 'BBBB' ? B : A] };
  }
  const id = p.includes(B) ? B : A;
  if (p.endsWith('/events')) {
    const later = parsed.searchParams.has('cursor');
    const count = options.pagination && !later ? 100 : 1;
    return { ...envelope, events: Array.from({ length: count }, (_, index) => ({ ...records[id].latest_observed_event,
      form: id === A ? 'S-3' : 'S-1', event_id: id + ':event:' + (later ? 100 : index),
      source: { filing_url: 'https://www.sec.gov/Archives/edgar/data/' + (id === A ? '1' : '2') + '/filing.htm' } })),
      page: { next_cursor: options.pagination && !later ? id + ':event:99' : null } };
  }
  return { ...envelope, issuer: records[id] };
}

function stubDom() {
  class Element {
    constructor() {
      this.hidden = false; this.innerHTML = ''; this.textContent = ''; this.attributes = {}; this.listeners = {};
      const classes = new Set();
      this.classList = { toggle(name, value) { if (value) classes.add(name); else classes.delete(name); }, add(name) { classes.add(name); }, remove(name) { classes.delete(name); }, contains(name) { return classes.has(name); } };
    }
    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
    dispatchEvent(event) { for (const handler of this.listeners[event.type] || []) handler(event); }
    getAttribute(name) { return this.attributes[name] ?? null; }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    removeAttribute(name) { delete this.attributes[name]; }
    focus() { doc.activeElement = this; }
    click() { if (!this.disabled) this.dispatchEvent({ type: 'click', target: this }); }
    querySelectorAll() { return []; }
  }
  const nodes = {};
  const doc = new Element();
  doc.readyState = 'complete';
  doc.documentElement = new Element();
  doc.body = new Element();
  doc.getElementById = id => (nodes[id] ||= new Element());
  const siteNav = new Element();
  doc.querySelector = query => query === '.site-nav' ? siteNav : null;
  doc.querySelectorAll = () => [];
  const win = new Element();
  win.location = { href: 'https://example.test/capital_structure.html', origin: 'https://example.test' };
  const history = [win.location.href];
  let historyIndex = 0;
  win.history = {
    get length() { return history.length; },
    pushState(_s, _t, href) { win.location.href = new URL(href, win.location.href).href; history.splice(++historyIndex); history.push(win.location.href); },
    replaceState(_s, _t, href) { win.location.href = new URL(href, win.location.href).href; history[historyIndex] = win.location.href; },
    back() { if (historyIndex > 0) { win.location.href = history[--historyIndex]; win.dispatchEvent({ type: 'popstate' }); } }
  };
  win.requestAnimationFrame = fn => fn();
  win.CustomEvent = class { constructor(type, options) { this.type = type; this.detail = options.detail; } };
  win.document = doc;
  win.close = () => {};
  doc.getElementById('cs-loading-template').innerHTML = '<div role="status">Loading observed filing state</div>';
  doc.getElementById('cs-dossier-body').hidden = true;
  doc.getElementById('cs-evidence-drawer').hidden = true;
  doc.getElementById('cs-scrim').hidden = true;
  return { window: win, evaluate() { vm.runInNewContext(source, { window: win, document: doc, fetch: win.fetch, URL, Date, Number, Array, Promise, console }); } };
}

async function desk(options = {}) {
  let env;
  if (native) {
    const { JSDOM } = require('jsdom');
    const html = fs.readFileSync(path.join(root, 'site/capital_structure.html'), 'utf8');
    const dom = new JSDOM(html, { url: 'https://example.test/capital_structure.html', runScripts: 'outside-only', pretendToBeVisual: true });
    await new Promise(resolve => dom.window.document.readyState === 'loading' ? dom.window.document.addEventListener('DOMContentLoaded', resolve, { once: true }) : resolve());
    env = { window: dom.window, evaluate() { dom.window.eval(source); } };
  } else env = stubDom();
  const w = env.window;
  const d = w.document;
  let hold = options.initialHold === true;
  const queued = [];
  const calls = [];
  const response = (url, status) => ({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(bodyFor(url, options)) });
  w.fetch = url => {
    calls.push(url);
    if (!hold) return Promise.resolve(response(url, 200));
    return new Promise((resolve, reject) => queued.push({ url, resolve, reject }));
  };
  env.evaluate();
  await flush();
  function select(id) {
    if (native) d.querySelector('[data-issuer-id="' + id + '"]').click();
    else d.getElementById('cs-issuer-list').dispatchEvent({ type: 'click', target: { closest() { return { getAttribute() { return id; } }; } } });
  }
  function selectVisible(id) {
    if (native) {
      const row = d.querySelector('[data-issuer-id="' + id + '"]');
      assert.ok(row && row.isConnected && !row.disabled && !row.closest('[hidden], [inert]'), 'resolver scenario selects a reachable enabled row');
    }
    select(id);
  }
  function language(value) {
    d.documentElement.setAttribute('data-lang', value);
    d.dispatchEvent(new w.CustomEvent('langchange', { detail: value }));
  }
  function snapshot() {
    const markup = d.getElementById('cs-issuer-list').innerHTML;
    const selected = native ? d.querySelector('[data-issuer-id][aria-current="true"]')?.getAttribute('data-issuer-id') : (markup.match(/data-issuer-id="([^"]+)" aria-current="true"/) || [])[1];
    return { url: new URL(w.location.href).searchParams.get('issuer'), selected,
      query: d.getElementById('cs-search-input').value || '', notice: d.getElementById('cs-coverage-state').textContent, historyLength: w.history.length,
      visible: !d.getElementById('cs-dossier-body').hidden, emptyVisible: !d.getElementById('cs-empty-dossier').hidden,
      name: d.getElementById('cs-dossier-title-live').textContent, error: d.getElementById('cs-empty-dossier').innerHTML,
      events: d.getElementById('cs-event-list').innerHTML,
      moreHidden: d.getElementById('cs-more-events').hidden, moreDisabled: d.getElementById('cs-more-events').disabled,
      drawerHidden: d.getElementById('cs-evidence-drawer').hidden, drawerOpen: d.getElementById('cs-evidence-drawer').classList.contains('is-open'),
      drawerHtml: d.getElementById('cs-evidence-body').innerHTML, evidenceDisabled: d.getElementById('cs-open-evidence').disabled,
      scrimHidden: d.getElementById('cs-scrim').hidden, modalOpen: d.body.classList.contains('cs-modal-open'),
      shellInert: d.getElementById('cs-shell').getAttribute('inert') !== null,
      navInert: d.querySelector('.site-nav').getAttribute('inert') !== null,
      dossierFocused: d.activeElement === d.getElementById('cs-dossier'), evidenceFocused: d.activeElement === d.getElementById('cs-open-evidence') };
  }
  async function takeRequests() { await flush(); return queued.splice(0); }
  async function settle(requests, status = 200, failEventsOnly = false) {
    for (const req of requests) {
      const actual = failEventsOnly && !req.url.includes('/events?') ? 200 : status;
      if (actual === 'network') req.reject(new Error('offline'));
      else req.resolve(response(req.url, actual));
    }
    await flush();
  }
  function type(value) {
    const input = d.getElementById('cs-search-input');
    assert.ok(!input.disabled, 'search input is enabled');
    input.focus(); input.value = value;
    input.dispatchEvent(native ? new w.InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }) : { type: 'input' });
  }
  function enter() {
    const input = d.getElementById('cs-search-input');
    assert.ok(!input.disabled, 'search input is enabled');
    input.dispatchEvent(native ? new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }) : { type: 'keydown', key: 'Enter' });
  }
  async function settleLookup(requests, outcome = 200) {
    assert.equal(requests.length, 1, 'one exact-ticker resolver request');
    assert.ok(requests[0].url.includes('/issuers/resolve?ticker='));
    if (outcome === 'empty') requests[0].resolve({ ok: true, status: 200, json: () => Promise.resolve({ ...envelope, query: { ticker: 'BBBB' } }) });
    else if (outcome === 409) requests[0].resolve({ ok: false, status: 409, json: () => Promise.resolve({ detail: { code: 'ambiguous_ticker', matches: [{ issuer_id: A }, { issuer_id: B }] } }) });
    else await settle(requests, outcome);
    await flush();
  }
  async function back() {
    if (native) await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('history Back did not emit popstate')), 1000);
      w.addEventListener('popstate', () => { clearTimeout(timeout); resolve(); }, { once: true });
      w.history.back();
    });
    else w.history.back();
    await flush();
  }
  if (!options.initialHold) assert.equal(snapshot().name, 'Issuer A');
  return { window: w, select, language, snapshot, takeRequests, settle, calls, type, enter, settleLookup, back, selectVisible,
    more() { d.getElementById('cs-more-events').click(); },
    openEvidence() { d.getElementById('cs-open-evidence').focus(); d.getElementById('cs-open-evidence').click(); },
    closeEvidence() { d.getElementById('cs-close-evidence').click(); },
    history(id) { w.history.pushState({}, '', '?issuer=' + encodeURIComponent(id)); w.dispatchEvent(native ? new w.PopStateEvent('popstate') : { type: 'popstate' }); },
    hold() { hold = true; }, close() { w.close(); } };
}

const results = [];
async function test(name, run) {
  try { await run(); results.push({ name, pass: true }); }
  catch (error) { results.push({ name, pass: false, error: error.message }); }
}
function selected(snapshot, id) { assert.equal(snapshot.url, id); assert.equal(snapshot.selected, id); }

(async () => {
  await test('language change preserves a pending issuer selection', async () => {
    const app = await desk();
    try {
      app.hold(); app.select(B); const pending = await app.takeRequests();
      for (const language of ['zh', 'en', 'zh']) {
        app.language(language); const s = app.snapshot(); selected(s, B);
        assert.equal(s.visible, false, 'a previous issuer must stay hidden while B loads'); assert.equal(s.emptyVisible, true);
      }
      await app.settle(pending); selected(app.snapshot(), B); assert.equal(app.snapshot().name, 'Issuer B');
      for (const language of ['en', 'zh']) { app.language(language); assert.equal(app.snapshot().name, 'Issuer B'); assert.equal(app.snapshot().visible, true); }
    } finally { app.close(); }
  });
  for (const status of [503, 403, 401, 'network']) {
    await test('language change preserves error ' + status + ' and retry recovery', async () => {
      const app = await desk();
      try {
        app.hold(); app.select(B); await app.settle(await app.takeRequests(), status);
        for (const language of ['zh', 'en', 'zh']) {
          app.language(language); const s = app.snapshot(); selected(s, B);
          assert.equal(s.visible, false, 'a failed B must not show cached A'); assert.equal(s.emptyVisible, true);
          const denied = status === 401 || status === 403;
          assert.ok(s.error.includes(language === 'zh' ? '记录暂不可用' : 'Record unavailable'));
          assert.ok(s.error.includes(language === 'zh' ? denied ? '符合条件的账户' : '请稍后重试' : denied ? 'eligible account' : 'Try again shortly'));
        }
        app.select(B); const retry = await app.takeRequests(); app.language('en'); assert.equal(app.snapshot().visible, false);
        await app.settle(retry); selected(app.snapshot(), B); assert.equal(app.snapshot().name, 'Issuer B'); assert.equal(app.snapshot().visible, true);
      } finally { app.close(); }
    });
  }
  await test('failed events endpoint keeps the whole dossier unavailable', async () => {
    const app = await desk();
    try { app.hold(); app.select(B); await app.settle(await app.takeRequests(), 503, true); app.language('zh'); assert.equal(app.snapshot().visible, false); assert.ok(app.snapshot().error.includes('记录暂不可用')); }
    finally { app.close(); }
  });
  await test('same-issuer failed refresh does not resurrect its cached dossier', async () => {
    const app = await desk();
    try { app.hold(); app.select(A); await app.settle(await app.takeRequests(), 503); app.language('zh'); selected(app.snapshot(), A); assert.equal(app.snapshot().visible, false); }
    finally { app.close(); }
  });
  for (const lateStatus of [200, 503]) {
    await test('late B response ' + lateStatus + ' cannot change newer A selection', async () => {
      const app = await desk();
      try {
        app.hold(); app.select(B); const old = await app.takeRequests(); app.select(A); const newer = await app.takeRequests();
        app.language('zh'); selected(app.snapshot(), A); assert.equal(app.snapshot().visible, false);
        await app.settle(newer); assert.equal(app.snapshot().name, 'Issuer A');
        await app.settle(old, lateStatus); app.language('en'); selected(app.snapshot(), A); assert.equal(app.snapshot().name, 'Issuer A'); assert.equal(app.snapshot().visible, true);
      } finally { app.close(); }
    });
  }
  for (const status of [200, 503]) {
    await test('superseded pagination ' + status + ' cannot change current B rows or cursor', async () => {
      const app = await desk({ pagination: true });
      try {
        app.hold(); app.more(); const old = await app.takeRequests(); assert.equal(old.length, 1);
        app.select(B); await app.settle(await app.takeRequests()); const before = app.snapshot();
        await app.settle(old, status); const after = app.snapshot();
        selected(after, B); assert.equal(after.events, before.events); assert.equal(after.moreHidden, false); assert.equal(after.moreDisabled, false);
      } finally { app.close(); }
    });
  }
  await test('superseded page finally cannot unlock a newer pending page', async () => {
    const app = await desk({ pagination: true });
    try {
      app.hold(); app.more(); const old = await app.takeRequests();
      app.select(B); await app.settle(await app.takeRequests());
      app.more(); const newer = await app.takeRequests(); assert.equal(newer.length, 1);
      await app.settle(old); assert.equal(app.snapshot().moreDisabled, true);
      await app.settle(newer); assert.equal(app.snapshot().moreDisabled, false); assert.equal(app.snapshot().moreHidden, true);
      assert.ok(!app.snapshot().events.includes('S-3'));
    } finally { app.close(); }
  });
  await test('same-issuer refresh invalidates an older pending page', async () => {
    const app = await desk({ pagination: true });
    try {
      app.hold(); app.more(); const old = await app.takeRequests(); app.select(A); await app.settle(await app.takeRequests());
      const before = app.snapshot(); await app.settle(old); assert.equal(app.snapshot().events, before.events); assert.equal(app.snapshot().moreHidden, false);
    } finally { app.close(); }
  });
  await test('current page failure preserves its cursor for a successful retry', async () => {
    const app = await desk({ pagination: true });
    try {
      app.hold(); const before = app.snapshot(); app.more(); const first = await app.takeRequests(); await app.settle(first, 503);
      assert.equal(app.snapshot().events, before.events); assert.equal(app.snapshot().moreHidden, false); assert.equal(app.snapshot().moreDisabled, false);
      app.more(); const retry = await app.takeRequests(); assert.equal(retry.length, 1); assert.equal(retry[0].url, first[0].url);
      await app.settle(retry); assert.equal(app.snapshot().moreHidden, true); assert.ok(app.snapshot().events.length > before.events.length);
    } finally { app.close(); }
  });
  for (const navigation of ['row', 'history']) {
    await test(navigation + ' transition closes and clears the previous evidence drawer', async () => {
      const app = await desk();
      try {
        app.openEvidence(); await new Promise(resolve => setTimeout(resolve, 30)); assert.equal(app.snapshot().drawerHidden, false);
        app.hold(); if (navigation === 'row') app.select(B); else app.history(B);
        const pending = await app.takeRequests(); const s = app.snapshot(); selected(s, B);
        assert.equal(s.drawerHidden, true); assert.equal(s.drawerOpen, false); assert.equal(s.drawerHtml, ''); assert.equal(s.evidenceDisabled, true);
        assert.equal(s.scrimHidden, true); assert.equal(s.modalOpen, false); assert.equal(s.shellInert, false); assert.equal(s.navInert, false); assert.equal(s.dossierFocused, true);
        await app.settle(pending); app.openEvidence(); await new Promise(resolve => setTimeout(resolve, 30));
        assert.ok(app.snapshot().drawerHtml.includes('/data/2/')); assert.ok(!app.snapshot().drawerHtml.includes('/data/1/'));
        app.closeEvidence(); assert.equal(app.snapshot().evidenceFocused, true); assert.equal(app.snapshot().modalOpen, false);
      } finally { app.close(); }
    });
  }
  await test('navigation cancels a not-yet-painted drawer open', async () => {
    const app = await desk();
    try {
      app.openEvidence(); app.hold(); app.history(B); await app.takeRequests(); await new Promise(resolve => setTimeout(resolve, 30));
      assert.equal(app.snapshot().drawerHidden, true); assert.equal(app.snapshot().drawerOpen, false); assert.equal(app.snapshot().dossierFocused, true);
    } finally { app.close(); }
  });

  for (const navigation of ['newer Enter', 'explicit row', 'browser Back']) {
    for (const outcome of [200, 409, 401, 403, 'empty', 'network']) {
      await test('superseded resolver ' + outcome + ' preserves ' + navigation, async () => {
        const app = await desk();
        try {
          app.hold();
          if (navigation === 'browser Back') { app.selectVisible(B); await app.settle(await app.takeRequests()); }
          app.type('BBBB'); app.enter(); const old = await app.takeRequests();
          let newer;
          if (navigation === 'newer Enter') {
            app.type('AAAA'); app.enter(); newer = await app.takeRequests();
          } else {
            app.type('');
            if (navigation === 'explicit row') app.selectVisible(A); else await app.back();
            await app.settle(await app.takeRequests());
          }
          const before = app.snapshot();
          await app.settleLookup(old, outcome);
          assert.deepEqual(app.snapshot(), before, 'obsolete resolver must not navigate, focus or replace the current notice');
          assert.equal((await app.takeRequests()).length, 0, 'obsolete resolver must not fetch another dossier');
          if (newer) {
            await app.settleLookup(newer); await app.settle(await app.takeRequests());
            selected(app.snapshot(), A); assert.equal(app.snapshot().name, 'Issuer A');
          }
        } finally { app.close(); }
      });
    }
  }
  await test('latest Enter also owns repeated same-ticker requests', async () => {
    const app = await desk();
    try {
      app.hold(); app.type('BBBB'); app.enter(); const old = await app.takeRequests();
      app.enter(); const newer = await app.takeRequests(); const before = app.snapshot();
      await app.settleLookup(old); assert.deepEqual(app.snapshot(), before); assert.equal((await app.takeRequests()).length, 0);
      await app.settleLookup(newer); await app.settle(await app.takeRequests());
      selected(app.snapshot(), B); assert.equal(app.snapshot().name, 'Issuer B');
    } finally { app.close(); }
  });
  for (const outcome of [200, 409, 401, 403, 503, 'empty', 'network']) {
    await test(outcome === 200 ? 'current resolver success selects the canonical issuer' : 'current resolver ' + outcome + ' preserves failure handling and retry', async () => {
      const app = await desk();
      try {
        app.hold(); app.type('  BBBB  '); app.enter(); const request = await app.takeRequests();
        assert.ok(request[0].url.endsWith('ticker=BBBB'), 'exact ticker is trimmed before API resolution');
        await app.settleLookup(request, outcome);
        if (outcome !== 200) {
          assert.equal(app.snapshot().url, A); assert.equal(app.snapshot().name, 'Issuer A');
          assert.equal(app.snapshot().notice, outcome === 'empty' ? 'No observed issuer matched that ticker' : 'Ticker lookup is temporarily unavailable');
          assert.equal((await app.takeRequests()).length, 0, 'failed or ambiguous lookup never guesses an issuer');
          app.enter(); await app.settleLookup(await app.takeRequests());
        }
        const dossier = await app.takeRequests();
        assert.equal(dossier.length, 2);
        assert.ok(dossier.every(req => decodeURIComponent(req.url).includes('/issuers/' + B)), 'canonical API issuer ID owns dossier requests');
        await app.settle(dossier); selected(app.snapshot(), B); assert.equal(app.snapshot().name, 'Issuer B');
      } finally { app.close(); }
    });
  }
  await test('query-only edits preserve an already submitted exact-ticker lookup', async () => {
    const app = await desk();
    try {
      app.hold(); app.type('BBBB'); app.enter(); const request = await app.takeRequests();
      app.type('AAAA'); await app.settleLookup(request); await app.settle(await app.takeRequests());
      assert.equal(app.snapshot().query, 'AAAA'); assert.equal(app.snapshot().url, B); assert.equal(app.snapshot().name, 'Issuer B');
    } finally { app.close(); }
  });

  for (const initialReady of [false, true]) {
    for (const outcome of [200, 'empty', 409, 401, 403, 503, 'network']) {
      await test('lookup submitted during startup survives automatic ' + (initialReady ? 'ready' : 'pending') + ' dossier: ' + outcome, async () => {
        const app = await desk({ initialHold: true });
        try {
          const initial = await app.takeRequests(); assert.equal(initial.length, 2);
          app.type('BBBB'); app.enter(); const lookup = await app.takeRequests();
          await app.settle(initial); const automatic = await app.takeRequests(); assert.equal(automatic.length, 2);
          if (initialReady) await app.settle(automatic);
          await app.settleLookup(lookup, outcome);
          if (outcome === 200) {
            const resolved = await app.takeRequests(); assert.equal(resolved.length, 2, 'automatic initialization does not cancel an explicit lookup');
            await app.settle(resolved);
            if (!initialReady) await app.settle(automatic);
            selected(app.snapshot(), B); assert.equal(app.snapshot().name, 'Issuer B');
          } else {
            assert.equal((await app.takeRequests()).length, 0, 'lookup failure does not fabricate a dossier');
            assert.equal(app.snapshot().notice, outcome === 'empty' ? 'No observed issuer matched that ticker' : 'Ticker lookup is temporarily unavailable');
            if (!initialReady) await app.settle(automatic);
            assert.equal(app.snapshot().url, A); assert.equal(app.snapshot().name, 'Issuer A');
            app.enter(); await app.settleLookup(await app.takeRequests()); await app.settle(await app.takeRequests());
            selected(app.snapshot(), B); assert.equal(app.snapshot().name, 'Issuer B');
          }
        } finally { app.close(); }
      });
    }
    for (const outcome of [200, 'empty', 401]) {
      await test('explicit row supersedes startup lookup after automatic ' + (initialReady ? 'ready' : 'pending') + ' dossier: ' + outcome, async () => {
        const app = await desk({ initialHold: true });
        try {
          const initial = await app.takeRequests();
          app.type('BBBB'); app.enter(); const lookup = await app.takeRequests();
          await app.settle(initial); const automatic = await app.takeRequests();
          if (initialReady) await app.settle(automatic);
          app.type(''); app.selectVisible(A); await app.settle(await app.takeRequests());
          const before = app.snapshot(); await app.settleLookup(lookup, outcome);
          assert.deepEqual(app.snapshot(), before); assert.equal((await app.takeRequests()).length, 0);
          if (!initialReady) await app.settle(automatic);
          selected(app.snapshot(), A); assert.equal(app.snapshot().name, 'Issuer A');
        } finally { app.close(); }
      });
    }
  }
  console.log(JSON.stringify({ mode: native ? 'jsdom' : 'dependency-free', results }, null, 2));
  if (results.some(item => !item.pass)) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });

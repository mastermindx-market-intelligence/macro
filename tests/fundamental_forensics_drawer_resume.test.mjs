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
      toggle(name, force) { if (force) classes.add(name); else classes.delete(name); },
    },
    hidden: true,
    disabled: false,
    innerHTML: '',
    textContent: '',
    value: '',
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
    focus() { this.focused = true; },
    contains() { return false; },
    style: {},
    insertAdjacentHTML(position, html) { this.innerHTML = position === 'afterbegin' ? html + this.innerHTML : this.innerHTML + html; },
  };
}

function harness(controls = [], settings = {}) {
  const nodes = {
    'ff-evidence': element(),
    'ff-evidence-body': element(),
    'ff-evidence-title': element(),
    'ff-evidence-close': element(),
    'ff-workspace': element(),
    'ff-scrim': element(),
    'ff-run-meta': element(),
    'ff-freshness-status': element(),
    'ff-as-of': element(),
    'ff-source-snapshot': element(),
    'ff-source-label': element(),
    'ff-desk-stamp': element(),
    'ff-main': element(),
    'ff-gate': element(),
    'ff-gate-state': element(),
    'ff-view-status': element(),
  };
  const windowListeners = {};
  const pushes = [];
  const replaces = [];
  const backs = [];
  const location = {
    hostname: 'contract.test',
    pathname: '/fundamental_forensics.html',
    search: '',
    hash: '',
  };
  const documentObject = {
    readyState: 'loading',
    addEventListener() {},
    getElementById: (id) => nodes[id] || (nodes[id] = element()),
    querySelector(selector) {
      if (selector.includes('data-occurrence-id')) return controls.find(c => selector.includes(c.getAttribute('data-occurrence-id'))) || null;
      if (selector.includes('data-root-cell-id')) return controls.find(c => selector.includes(c.getAttribute('data-root-cell-id'))) || null;
      return element();
    },
    querySelectorAll(selector) { return selector.includes('.ff-source-control') ? controls : []; },
    createElement: () => element(),
    body: { classList: { add() {}, remove() {} }, appendChild() {}, removeChild() {} },
    documentElement: { getAttribute(name) { return name === 'data-theme' ? settings.theme || 'dark' : settings.locale || 'en'; } },
    activeElement: null,
  };
  const windowObject = {
    location,
    matchMedia: () => ({ matches: settings.width !== 390, addEventListener() {}, addListener() {} }),
    __FF_WORKBENCH_TEST__: true,
    requestAnimationFrame(fn) { fn(); },
    setTimeout(fn) { fn(); },
    addEventListener: (name, handler) => {
      windowListeners[name] = windowListeners[name] || [];
      windowListeners[name].push(handler);
    },
    history: {
      state: null,
      back() { backs.push(true); },
      pushState: (state, title, url) => { windowObject.history.state = state; pushes.push(String(url)); location.search = String(url).replace(/^[^?]*/, '') || ''; },
      replaceState: (state, title, url) => { windowObject.history.state = state; replaces.push(String(url)); location.search = String(url).replace(/^[^?]*/, '') || ''; },
    },
    fetch: settings.fetch || (() => new Promise(() => {})),
    URL,
    URLSearchParams,
  };
  const context = vm.createContext({
    window: windowObject,
    document: documentObject,
    console,
    URL,
    URLSearchParams,
    TextDecoder, Response, Blob, fetch: windowObject.fetch,
  });
  vm.runInContext(source, context, { filename: 'fundamental_forensics.js' });
  const api = windowObject.__FF_WORKBENCH_TEST__;
  api.cacheUi();
  api.ui.evidence = nodes['ff-evidence'];
  api.ui.evidenceBody = nodes['ff-evidence-body'];
  api.ui.evidenceTitle = nodes['ff-evidence-title'];
  api.ui.evidenceClose = nodes['ff-evidence-close'];
  api.ui.workspace = nodes['ff-workspace'];
  api.ui.scrim = nodes['ff-scrim'];
  api.ui.main = nodes['ff-main'];
  api.ui.siteNav = element();
  api.ui.runMeta = nodes['ff-run-meta'];
  return { api, nodes, windowListeners, pushes, replaces, location, controls, backs };
}


// UI-only synthetic identifiers. No economic facts, private issuer payload or
// entitlement/current-served claim is supplied by this offline controller test.
const fixtureFinding = { id: 'fixture-finding', title_en: 'Non-economic UI fixture', title_zh: '非经济界面样本', period_current: 'UI-PERIOD', limitations: ['UI fixture only'] };
const frame = '?symbol=UIFIX&finding=fixture-finding&drawer=1&occ=fixture-occ&cell=fixture-cell&snap=fixture-snapshot&span=10-20';
function sourceControl() {
  const c = element();
  for (const [name, value] of Object.entries({
    'data-source-kind': 'cell', 'data-occurrence-id': 'fixture-occ',
    'data-root-cell-id': 'fixture-cell', 'data-snapshot-id': 'fixture-snapshot',
    'data-span-start': '10', 'data-span-end': '20',
  })) c.setAttribute(name, value);
  return c;
}
function admitUiSource(h) {
  // Already admitted owner state only; this fixture asserts no economic truth.
  h.api.state.financial = { phase: 'ready', asReported: [], latest: [], restated: [], revisions: [] };
  h.api.state.queryNodes = [{ value: '123.00', unit: 'UI-FIXTURE',
    cell_id: 'fixture-cell', snapshot_id: 'fixture-snapshot',
    provenance: { selected_raw_fact: { occurrence_id: 'fixture-occ', source_span: { start: 10, end: 20 } } }
  }];
}
function ready(controls = [sourceControl()]) {
  const h = harness(controls);
  h.api.state.payload = { companies: { UIFIX: { symbol: 'UIFIX', periods: [], findings: [fixtureFinding] } }, default_symbol: 'UIFIX' };
  h.api.state.symbol = 'UIFIX'; h.api.state.findingId = 'fixture-finding'; h.api.state.access = 'open';
  admitUiSource(h);
  h.location.search = frame;
  return h;
}
function pop(h) { h.api.bindEvents(); h.windowListeners.popstate[0](); }
test('initial hydrate preserves the exact source drawer URL tuple', () => {
  const h = ready(); h.api.applyUrlState(true);
  const restored = h.api.readUrlParams();
  assert.equal(restored.drawer, true);
  for (const key of ['occ', 'cell', 'snap', 'span'])
    assert.equal(restored[key], new URLSearchParams(frame).get(key));
});
test('Back/Forward restores the source drawer without pushing another frame', () => {
  const h = ready(); pop(h);
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), true);
  assert.equal(h.pushes.length, 0);
  assert.equal(h.api.state.cellEvidence.snapshotId, 'fixture-snapshot');
});
for (const [name, query] of [
  ['unknown snapshot', frame.replace('fixture-snapshot', 'unknown-snapshot')],
  ['wrong cell', frame.replace('fixture-cell', 'other-cell')],
  ['wrong span', frame.replace('10-20', '20-30')],
  ['malformed span', frame.replace('10-20', 'bad')],
  ['unknown company', frame.replace('UIFIX', 'UNKNOWN')],
]) test(`${name} never opens a different source`, () => {
  const h = ready(); h.location.search = query; pop(h);
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), false);
  assert.equal(h.pushes.length, 0);
});

for (const [name, query] of [
  ['missing snapshot', frame.replace('&snap=fixture-snapshot', '')],
  ['query selector syntax', frame.replace('fixture-occ', 'fixture-occ%22%5D')],
  ['duplicate snapshot', frame + '&snap=fixture-snapshot'],
  ['invalid cutoff', frame + '&as_of=2026-02-30'],
  ['invalid policy', frame + '&policy=imaginary'],
  ['invalid tab', frame + '&tab=imaginary'],
  ['reversed span', frame.replace('10-20', '20-10')],
  ['unknown finding', frame.replace('fixture-finding', 'unknown-finding')],
  ['unknown disclosure', frame + '&disc=unknown-disclosure'],
  ['unknown redline', frame + '&redline=unknown-redline'],
]) test(`${name} refuses without rewriting the requested identity`, () => {
  const h = ready(); h.location.search = query;
  h.api.applyUrlState(true); const untouched = h.location.search;
  pop(h);
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), false);
  assert.equal(h.api.state.cellEvidence, null);
  assert.equal(h.location.search, untouched);
  assert.equal(h.pushes.length, 0);
  assert.match(h.nodes['ff-evidence-body'].innerHTML, /Exact value unavailable/);
});
test('cold entry waits for the real loaded source owner before restoring its preserved address', async () => {
  const payload = { companies: { UIFIX: { symbol: 'UIFIX', name: 'Non-economic UI fixture', periods: [], findings: [fixtureFinding] } }, default_symbol: 'UIFIX' };
  const requests = [];
  const h = harness([sourceControl()], { fetch: async url => {
    requests.push(url);
    if (url === '/api/forensics/state') return new Response(JSON.stringify(payload), { status: 200 });
    return new Promise(() => {}); // incumbent health, no network or provider
  } });
  h.location.search = frame;
  await h.api.loadData();
  assert.equal(h.api.state.access, 'open');
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), false);
  assert.equal(h.api.readUrlParams().drawer, true);
  admitUiSource(h); h.api.renderRevisions();
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), true);
  assert.equal(h.api.state.cellEvidence.snapshotId, 'fixture-snapshot');
  assert.equal(h.api.state.cellEvidence.exactText, '123.00');
  assert.equal(h.pushes.length, 0);
  assert.equal(requests.filter(u => u === '/api/forensics/state').length, 1);
  assert.ok(requests.every(u => ['/api/forensics/state', '/api/forensics/health'].includes(u)));
});
test('late incumbent statement render restores a matching source but cannot revive a changed URL', () => {
  const h = ready([]);
  h.api.applyUrlState(true);
  assert.equal(h.api.openDrawerFromUrl(h.api.readUrlParams()), false);
  h.api.state.statements = { phase: 'ready', statements: [] };
  h.controls.push(sourceControl()); h.api.renderStatementTree();
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), true);
  assert.equal(h.pushes.length, 0);
  h.location.search = '?symbol=UIFIX';
  pop(h); h.api.renderStatementTree();
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), false);
});
test('direct-entry close rewrites the desk; click-created close backs out once and restores exact focus', () => {
  const h = ready(); h.api.applyUrlState(true); h.api.openDrawerFromUrl(h.api.readUrlParams());
  h.api.closeDrawerAndSync();
  assert.equal(h.backs.length, 0);
  assert.equal(h.api.readUrlParams().drawer, false);
  h.api.activateSourceControl(h.controls[0]);
  assert.equal(h.pushes.length, 1);
  assert.equal(h.api.state.lastFocus, h.controls[0]);
  h.api.closeDrawerAndSync();
  assert.equal(h.backs.length, 1);
  assert.equal(h.controls[0].focused, true);
});
test('changed snapshot closes an already open source without retaining its evidence', () => {
  const h = ready(); pop(h);
  h.location.search = frame.replace('fixture-snapshot', 'unknown-snapshot');
  h.windowListeners.popstate[0]();
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), false);
  assert.equal(h.api.state.cellEvidence, null);
  assert.equal(h.pushes.length, 0);
});

test('a stale DOM control cannot substitute for an unavailable or newer source owner', () => {
  const h = ready(); h.api.state.financial.phase = 'loading'; pop(h);
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), false);
  h.api.state.financial.phase = 'ready'; h.api.state.queryNodes[0].snapshot_id = 'newer-snapshot';
  h.api.openDrawerFromUrl(h.api.readUrlParams());
  assert.equal(h.nodes['ff-evidence'].classList.contains('is-open'), false);
  assert.equal(h.api.state.cellEvidence, null);
});

for (const locale of ['en', 'zh']) for (const theme of ['dark', 'light']) for (const width of [1440, 390]) {
  test(`semantic source and unavailable composition ${theme}/${locale}/${width} (no pixel claim)`, () => {
    const h = harness([sourceControl()], { locale, theme, width });
    h.api.state.payload = { companies: { UIFIX: { symbol: 'UIFIX', periods: [], findings: [fixtureFinding] } } };
    h.api.state.symbol = 'UIFIX'; h.api.state.findingId = 'fixture-finding'; h.api.state.access = 'open'; admitUiSource(h);
    h.location.search = frame;
    assert.equal(h.api.openDrawerFromUrl(h.api.readUrlParams()), true);
    assert.match(h.nodes['ff-evidence-body'].innerHTML, /123.00/);
    assert.match(h.nodes['ff-evidence-body'].innerHTML, /fixture-snapshot/);
    assert.equal(h.api.state.lastFocus, h.controls[0]);
    h.location.search = frame.replace('fixture-snapshot', 'missing-snapshot');
    assert.equal(h.api.openDrawerFromUrl(h.api.readUrlParams()), false);
    assert.equal(h.api.state.cellEvidence, null);
    assert.match(h.nodes['ff-evidence-body'].innerHTML, /requested source is unavailable/);
    assert.match(h.nodes['ff-evidence-body'].innerHTML, /所请求来源不可用/);
    assert.doesNotMatch(h.nodes['ff-evidence-body'].innerHTML, /123.00|href=/);
  });
}

test('reload preserves the return ownership of an existing click-created drawer frame', () => {
  const h = ready(); h.api.activateSourceControl(h.controls[0]);
  assert.equal(h.api.state.lastFocus, h.controls[0]);
  h.api.applyUrlState(true); h.api.openDrawerFromUrl(h.api.readUrlParams());
  assert.equal(h.pushes.length, 1);
  h.api.closeDrawerAndSync();
  assert.equal(h.backs.length, 1);
});

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
    focus() {},
    insertAdjacentHTML() {},
  };
}

function harness() {
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
  const location = {
    hostname: 'contract.test',
    pathname: '/fundamental_forensics.html',
    search: '',
    hash: '',
  };
  const documentObject = {
    readyState: 'loading',
    addEventListener() {},
    getElementById: (id) => nodes[id] || element(),
    querySelector() { return element(); },
    querySelectorAll() { return []; },
    createElement: () => element(),
    body: { classList: { add() {}, remove() {} }, appendChild() {}, removeChild() {} },
    documentElement: { getAttribute() { return 'en'; } },
    activeElement: null,
  };
  const windowObject = {
    location,
    matchMedia: () => ({ matches: true, addEventListener() {}, addListener() {} }),
    __FF_WORKBENCH_TEST__: true,
    requestAnimationFrame(fn) { fn(); },
    setTimeout(fn) { fn(); },
    addEventListener: (name, handler) => {
      windowListeners[name] = windowListeners[name] || [];
      windowListeners[name].push(handler);
    },
    history: {
      pushState: (state, title, url) => { pushes.push(String(url)); location.search = String(url).replace(/^[^?]*/, '') || ''; },
      replaceState: (state, title, url) => { replaces.push(String(url)); location.search = String(url).replace(/^[^?]*/, '') || ''; },
    },
    fetch: () => new Promise(() => {}),
    URL,
    URLSearchParams,
  };
  const context = vm.createContext({
    window: windowObject,
    document: documentObject,
    console,
    URL,
    URLSearchParams,
    TextDecoder,
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
  return { api, nodes, windowListeners, pushes, replaces, location };
}

test('writeUrl round-trips symbol, tab, as_of and the drawer frame', () => {
  const { api, pushes, location } = harness();
  api.state.symbol = 'AAPL';
  api.state.tab = 'compare';
  api.state.asOfDate = '2025-06-30';
  api.writeUrl(true);
  const deskUrl = pushes.at(-1);
  assert.match(deskUrl, /symbol=AAPL/);
  assert.match(deskUrl, /tab=compare/);
  assert.match(deskUrl, /as_of=2025-06-30/);
  location.search = deskUrl.replace(/^[^?]*/, '');
  let frame = api.readUrlParams();
  assert.equal(frame.symbol, 'AAPL');
  assert.equal(frame.tab, 'compare');
  assert.equal(frame.asOfDate, '2025-06-30');
  assert.equal(frame.drawer, false);

  api.writeUrl(true, {
    drawer: true,
    occ: 'rawfact_abc123',
    cell: 'metric_cell_deadbeef',
    snap: 'ffqsv2_cafe',
    span: '1200-1288'
  });
  const drawerUrl = pushes.at(-1);
  assert.match(drawerUrl, /drawer=1/);
  assert.match(drawerUrl, /occ=rawfact_abc123/);
  assert.match(drawerUrl, /cell=metric_cell_deadbeef/);
  assert.match(drawerUrl, /snap=ffqsv2_cafe/);
  assert.match(drawerUrl, /span=1200-1288/);
  location.search = drawerUrl.replace(/^[^?]*/, '');
  frame = api.readUrlParams();
  assert.equal(frame.drawer, true);
  assert.equal(frame.occ, 'rawfact_abc123');
  assert.equal(frame.cell, 'metric_cell_deadbeef');
  assert.equal(frame.snap, 'ffqsv2_cafe');
  assert.equal(frame.span, '1200-1288');
});

test('writeUrl drops defaults and ignores unknown input shapes', () => {
  const { api, pushes, location } = harness();
  api.state.symbol = 'MSFT';
  api.state.tab = 'radar';
  api.state.asOfDate = '';
  api.writeUrl(true);
  const url = pushes.at(-1);
  assert.match(url, /symbol=MSFT/);
  assert.doesNotMatch(url, /tab=/);
  assert.doesNotMatch(url, /as_of=/);
  assert.doesNotMatch(url, /drawer=/);
  location.search = '?symbol=MSFT&nonsense=1&tab=dragons&as_of=not-a-date&policy=chaos&span=abc';
  const frame = api.readUrlParams();
  assert.equal(frame.symbol, 'MSFT');
  assert.equal(frame.tab, 'radar');
  assert.equal(frame.asOfDate, '');
  assert.equal(frame.policy, 'latest_known_as_of');
  assert.equal(frame.span, '');
});

test('popstate closes an open drawer when the frame has no drawer param', () => {
  const { api, nodes, windowListeners, location } = harness();
  api.bindEvents();
  api.state.payload = { companies: { AAPL: {} }, default_symbol: 'AAPL' };
  api.state.symbol = 'AAPL';
  api.openAnalysisDrawer();
  assert.equal(nodes['ff-evidence'].classList.contains('is-open'), true);
  location.search = '?symbol=AAPL&tab=radar';
  const handlers = windowListeners.popstate || [];
  assert.ok(handlers.length >= 1, 'popstate handler registered');
  handlers.forEach((handler) => handler());
  assert.equal(nodes['ff-evidence'].classList.contains('is-open'), false);
});

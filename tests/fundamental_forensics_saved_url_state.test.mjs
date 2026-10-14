// FIF X2-s saved-views URL-state suite (hermetic: no network, no browser).
//
// The saved view's permalink is P2's existing URL writer — never a second
// builder. Pins: the permalink params a restore writes round-trip through
// readUrlParams (and applyUrlState) exactly; popstate restores the previous
// frame; unknown params stay ignored; the pinned cutoff rides as_of; the
// badge prints plain words (Pinned to … / As of … · latest), never slugs.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const BRIEFCASE_SOURCE = readFileSync(new URL('../templates/fif_saved_briefcase.js', import.meta.url), 'utf8');
const PAGE_SOURCE = readFileSync(new URL('../templates/fundamental_forensics.js', import.meta.url), 'utf8');
const FIXTURE_DIR = new URL('../tests/fixtures/fundamental_forensics/fif_saved_research/', import.meta.url);
const STORE_KEY = 'mastermind.filing_forensics.saved_research.v1';

function element() {
  const classes = new Set();
  const attrs = {};
  return {
    classList: {
      add: (name) => classes.add(name),
      remove: (name) => classes.delete(name),
      contains: (name) => classes.has(name),
      toggle: (name, force) => {
        const on = force === undefined ? !classes.has(name) : !!force;
        if (on) classes.add(name); else classes.delete(name);
        return on;
      },
    },
    hidden: true,
    disabled: false,
    innerHTML: '',
    textContent: '',
    value: '',
    placeholder: '',
    setAttribute: (key, value) => { attrs[key] = String(value); },
    removeAttribute: (key) => { delete attrs[key]; },
    getAttribute: (key) => (Object.prototype.hasOwnProperty.call(attrs, key) ? attrs[key] : null),
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    focus() {},
    insertAdjacentHTML() {},
  };
}

function harness() {
  const nodes = {};
  for (const id of [
    'ff-evidence', 'ff-evidence-body', 'ff-evidence-title', 'ff-evidence-close',
    'ff-workspace', 'ff-scrim', 'ff-run-meta', 'ff-freshness-status', 'ff-as-of',
    'ff-source-snapshot', 'ff-source-label', 'ff-desk-stamp', 'ff-main', 'ff-gate',
    'ff-gate-state', 'ff-view-status', 'ff-saved-controls', 'ff-saved-select',
    'ff-saved-name', 'ff-saved-save', 'ff-saved-rename', 'ff-saved-delete',
    'ff-saved-badge', 'ff-saved-notice', 'ff-peer-save-row', 'ff-peer-save',
    'ff-asof-latest', 'ff-asof-input'
  ]) nodes[id] = element();
  const windowListeners = {};
  const pushes = [];
  const location = {
    hostname: 'contract.test',
    pathname: '/fundamental_forensics.html',
    search: '',
    hash: ''
  };
  const storage = new Map();
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
    localStorage: {
      getItem: (key) => (storage.has(key) ? storage.get(key) : null),
      setItem: (key, value) => { storage.set(key, String(value)); },
    },
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
      replaceState: (state, title, url) => { location.search = String(url).replace(/^[^?]*/, '') || ''; },
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
  vm.runInContext(BRIEFCASE_SOURCE, context, { filename: 'fif_saved_briefcase.js' });
  vm.runInContext(PAGE_SOURCE, context, { filename: 'fundamental_forensics.js' });
  const api = windowObject.__FF_WORKBENCH_TEST__;
  api.cacheUi();
  api.ui.siteNav = element();
  api.ui.evidence = nodes['ff-evidence'];
  api.ui.workspace = nodes['ff-workspace'];
  api.ui.scrim = nodes['ff-scrim'];
  api.ui.main = nodes['ff-main'];
  api.ui.runMeta = nodes['ff-run-meta'];
  api.state.payload = {
    companies: {
      AAPL: {
        symbol: 'AAPL', name: 'Apple Inc.', cik: '0000320193', entity_id: 'ISS:US-XNAS-AAPL',
        sector: 'Information Technology', latest_filed: '2025-02-03', latest_period: 'FY2024',
        periods: [{ fiscal_year: 2024, start: '2023-10-01', end: '2024-09-28' }], findings: [], coverage: {}
      },
      MSFT: {
        symbol: 'MSFT', name: 'Microsoft Corp.', cik: '0000789019', entity_id: 'ISS:US-XNAS-MSFT',
        sector: 'Information Technology', latest_filed: '2025-01-29', latest_period: 'FY2024',
        periods: [{ fiscal_year: 2024, start: '2023-07-01', end: '2024-06-30' }], findings: [], coverage: {}
      }
    },
    default_symbol: 'AAPL',
    ranked_findings: []
  };
  api.state.symbol = 'AAPL';
  api.state.access = 'open';
  return { api, nodes, windowListeners, pushes, location, storage };
}

function seed(drive, name) {
  const container = JSON.parse(readFileSync(new URL(name, FIXTURE_DIR), 'utf8'));
  drive.storage.set(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  return container;
}

test('a restored view writes its permalink through P2\'s writer, params round-trip', () => {
  const drive = harness();
  const container = seed(drive, 'saved_cohort.json');
  drive.api.state.symbol = 'MSFT';
  const result = drive.api.restoreSavedView(container.saved_views[0].id);
  assert.equal(result.ok, true, result.reason || 'restore refused');
  const permalink = drive.pushes.at(-1);
  assert.match(permalink, /[?&]symbol=AAPL/);
  assert.match(permalink, /[?&]tab=peers/);
  assert.match(permalink, /[?&]cohort=cohort_2026q3_megacap/);
  assert.match(permalink, /[?&]peer_metric=revenue/);
  assert.match(permalink, /[?&]align=shift_labeled/);
  assert.match(permalink, /[?&]peer_n=5/);
  assert.match(permalink, /[?&]peer_tol=60/);

  drive.location.search = permalink.replace(/^[^?]*/, '');
  const frame = drive.api.readUrlParams();
  assert.equal(frame.symbol, 'AAPL');
  assert.equal(frame.tab, 'peers');
  assert.equal(frame.cohort, 'cohort_2026q3_megacap');
  assert.equal(frame.peerMetric, 'revenue');
  assert.equal(frame.align, 'shift_labeled');
  assert.equal(frame.peerN, 5);
  assert.equal(frame.peerTol, 60);
});

test('a pinned restore carries the cutoff day on as_of', () => {
  const drive = harness();
  const container = seed(drive, 'saved_pinned.json');
  drive.api.restoreSavedView(container.saved_views[0].id);
  const permalink = drive.pushes.at(-1);
  assert.match(permalink, /[?&]as_of=2026-09-30/);
  assert.match(permalink, /[?&]tab=compare/);
  drive.location.search = permalink.replace(/^[^?]*/, '');
  const frame = drive.api.readUrlParams();
  assert.equal(frame.asOfDate, '2026-09-30');
});

test('a pinned restore shows its cutoff on the as-of controls and the desk stamp', () => {
  const drive = harness();
  const container = seed(drive, 'saved_pinned.json');
  drive.api.restoreSavedView(container.saved_views[0].id);
  assert.equal(drive.nodes['ff-asof-input'].value, '2026-09-30', 'the date field carries the pinned cutoff');
  assert.equal(drive.nodes['ff-asof-latest'].classList.contains('is-active'), false, 'Latest is not pressed');
  assert.equal(drive.nodes['ff-asof-latest'].getAttribute('aria-pressed'), 'false');
  assert.match(drive.nodes['ff-desk-stamp'].innerHTML, /As of 2026-09-30 /);

  const latestDrive = harness();
  const latest = seed(latestDrive, 'saved_latest.json');
  latestDrive.api.restoreSavedView(latest.saved_views[0].id);
  assert.equal(latestDrive.nodes['ff-asof-input'].value, '', 'a latest view leaves the date field empty');
  assert.equal(latestDrive.nodes['ff-asof-latest'].classList.contains('is-active'), true, 'Latest is pressed');
  assert.equal(latestDrive.nodes['ff-asof-latest'].getAttribute('aria-pressed'), 'true');
});

test('popstate restores the previous frame and drops the restored-view context', () => {
  const drive = harness();
  const container = seed(drive, 'saved_cohort.json');
  drive.api.bindEvents();
  drive.api.state.symbol = 'MSFT';
  drive.api.restoreSavedView(container.saved_views[0].id);
  assert.equal(drive.api.state.cohortId, 'cohort_2026q3_megacap');
  assert.equal(drive.api.state.savedActiveId, container.saved_views[0].id);

  drive.location.search = '?symbol=MSFT&tab=radar';
  (drive.windowListeners.popstate || []).forEach((handler) => handler());
  assert.equal(drive.api.state.symbol, 'MSFT');
  assert.equal(drive.api.state.cohortId, '');
  assert.equal(drive.api.state.peerAlign, 'exclude');
  assert.equal(drive.api.state.peerN, 3);
  assert.equal(drive.api.state.peerTol, 45);
  assert.equal(drive.api.state.tab, 'radar');
  assert.equal(drive.api.state.savedActiveId, '');
});

test('unknown params are ignored alongside saved-view params', () => {
  const drive = harness();
  drive.location.search = '?symbol=AAPL&saved=dreams&tab=dragons&as_of=2025-06-30&policy=chaos&cohort=c1&peer_metric=revenue&align=shift_labeled&peer_n=5&peer_tol=60&nonsense=1';
  const frame = drive.api.readUrlParams();
  assert.equal(frame.symbol, 'AAPL');
  assert.equal(frame.tab, 'radar', 'unknown tab falls back to radar');
  assert.equal(frame.asOfDate, '2025-06-30');
  assert.equal(frame.policy, 'latest_known_as_of', 'unknown policy falls back');
  assert.equal(frame.cohort, 'c1');
  assert.equal(frame.peerMetric, 'revenue');
  assert.equal(frame.align, 'shift_labeled');
  assert.equal(frame.peerN, 5);
  assert.equal(frame.peerTol, 60);
});

test('the badge prints plain words for pinned and latest, never a policy slug', () => {
  const drive = harness();
  const container = seed(drive, 'saved_pinned.json');
  drive.api.restoreSavedView(container.saved_views[0].id);
  drive.api.renderSavedUI();
  const badge = drive.nodes['ff-saved-badge'];
  assert.equal(badge.hidden, false);
  assert.match(badge.innerHTML, /Pinned to 2026-09-30 · Latest known on that date/);
  assert.doesNotMatch(badge.innerHTML, /latest_known_as_of/);

  const latestDrive = harness();
  const latest = seed(latestDrive, 'saved_latest.json');
  latestDrive.api.restoreSavedView(latest.saved_views[0].id);
  latestDrive.api.renderSavedUI();
  assert.equal(latestDrive.nodes['ff-saved-badge'].hidden, false);
  assert.match(latestDrive.nodes['ff-saved-badge'].innerHTML, / · latest</);
});

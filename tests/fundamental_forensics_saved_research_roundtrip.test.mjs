// FIF X2-s saved-research roundtrip suite (hermetic: no network, no browser).
//
// Drives the real page module (templates/fundamental_forensics.js) and the
// real store module (templates/fif_saved_briefcase.js) inside a vm context
// with stubbed storage/fetch/crypto, over the committed fixtures. Pins:
//   - save -> reload (fresh module instance, same storage) -> identical bytes
//   - fixture identity: the module's saved object for fixed inputs equals the
//     committed fixture JSON (the Python schema suite walks the same files)
//   - restore of a pinned view re-POSTs the stored request bytes verbatim on
//     every leg (latest leg included) and the stubbed X-FIF-Response-SHA256
//     matches the served body
//   - direct link (P2 URL reader) and Back (popstate) restore
//     subject/policy/cutoff/cohort exactly
//   - every T1 refusal reason (exact strings), refused views staying listed +
//     deletable, and a drifted container going READ-ONLY, never blanked
//   - the store makes zero network calls, signed in and signed out, and
//     writes only its own localStorage key
//   - the A->B manifest mapping round-trips every fixture losslessly
//   - the evidence-harness seed container (rows 1-2 load, drift row refuses)
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const BRIEFCASE_SOURCE = readFileSync(new URL('../templates/fif_saved_briefcase.js', import.meta.url), 'utf8');
const PAGE_SOURCE = readFileSync(new URL('../templates/fundamental_forensics.js', import.meta.url), 'utf8');
const FIXTURE_DIR = new URL('../tests/fixtures/fundamental_forensics/fif_saved_research/', import.meta.url);
const RECORDED_BODY = readFileSync(new URL('recorded_query_response.json', FIXTURE_DIR), 'utf8');
const RECORDED_BYTES = new TextEncoder().encode(JSON.stringify(JSON.parse(RECORDED_BODY)));
const RECORDED_SHA = createHash('sha256').update(RECORDED_BYTES).digest('hex');

function fixtureContainer(name) {
  return JSON.parse(readFileSync(new URL(name, FIXTURE_DIR), 'utf8'));
}

// webcrypto.subtle.digest is genuinely async (thread pool): drain the page's
// promise chain deterministically instead of guessing a tick count.
async function untilFinancialSettled(api) {
  for (let attempt = 0; attempt < 100 && api.state.financial.phase === 'loading'; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1));
  }
}

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

function memoryStorage(initial) {
  const rows = new Map(initial || []);
  const written = [];
  return {
    rows,
    written,
    getItem: (key) => (rows.has(key) ? rows.get(key) : null),
    setItem: (key, value) => { rows.set(key, String(value)); written.push(key); },
    removeItem: (key) => { rows.delete(key); },
  };
}

// A storage whose writes always fail (MINOR-1: rollback + 'storage').
function failingStorage(existing) {
  const rows = new Map(existing || []);
  return {
    getItem: (key) => (rows.has(key) ? rows.get(key) : null),
    setItem: () => { throw new Error('quota exceeded'); },
    removeItem: (key) => { rows.delete(key); },
  };
}

// A storage whose FIRST write fails and can then be repaired, proving the
// failed attempt left no phantom state behind.
function onceFailingStorage() {
  const rows = new Map();
  let broken = true;
  return {
    getItem: (key) => (rows.has(key) ? rows.get(key) : null),
    setItem: (key, value) => { if (broken) throw new Error('quota exceeded'); rows.set(key, String(value)); },
    removeItem: (key) => { rows.delete(key); },
    repair: () => { broken = false; },
  };
}

// X2-s r2 (R2-2): the same once-failing contract over a PRE-POPULATED map,
// so the rollback tests seed their rows before the failing write. The
// existing stubs stay unchanged.
function onceFailingStorageWith(initialRows) {
  const rows = new Map(initialRows || []);
  let broken = true;
  return {
    getItem: (key) => (rows.has(key) ? rows.get(key) : null),
    setItem: (key, value) => { if (broken) throw new Error('quota exceeded'); rows.set(key, String(value)); },
    removeItem: (key) => { rows.delete(key); },
    repair: () => { broken = false; },
  };
}

const PAGE_PAYLOAD = {
  companies: {
    AAPL: {
      symbol: 'AAPL',
      name: 'Apple Inc.',
      cik: '0000320193',
      entity_id: 'ISS:US-XNAS-AAPL',
      sector: 'Information Technology',
      latest_filed: '2025-02-03',
      latest_period: 'FY2024',
      periods: [
        { fiscal_year: 2024, fiscal_quarter: 4, start: '2023-10-01', end: '2024-09-28' },
        { fiscal_year: 2023, fiscal_quarter: 4, start: '2022-09-25', end: '2023-09-30' }
      ],
      findings: [{ id: 'finding_aapl_receivables_growth', priority: 'watch', topic: 'receivables' }],
      coverage: {}
    },
    MSFT: {
      symbol: 'MSFT',
      name: 'Microsoft Corp.',
      cik: '0000789019',
      entity_id: 'ISS:US-XNAS-MSFT',
      sector: 'Information Technology',
      latest_filed: '2025-01-29',
      latest_period: 'FY2024',
      periods: [{ fiscal_year: 2024, start: '2023-07-01', end: '2024-06-30' }],
      findings: [],
      coverage: {}
    }
  },
  default_symbol: 'AAPL',
  ranked_findings: []
};

function harness(options) {
  options = options || {};
  const fetchCalls = [];
  const xhrCount = { count: 0 };
  const nodes = {};
  for (const id of [
    'ff-evidence', 'ff-evidence-body', 'ff-evidence-title', 'ff-evidence-close',
    'ff-workspace', 'ff-scrim', 'ff-run-meta', 'ff-freshness-status', 'ff-as-of',
    'ff-source-snapshot', 'ff-source-label', 'ff-desk-stamp', 'ff-main', 'ff-gate',
    'ff-gate-state', 'ff-view-status', 'ff-saved-controls', 'ff-saved-select',
    'ff-saved-name', 'ff-saved-save', 'ff-saved-rename', 'ff-saved-delete',
    'ff-saved-badge', 'ff-saved-notice', 'ff-peer-save-row', 'ff-peer-save'
  ]) nodes[id] = element();
  const windowListeners = {};
  const pushes = [];
  const replaces = [];
  const location = {
    hostname: 'contract.test',
    pathname: '/fundamental_forensics.html',
    search: '',
    hash: ''
  };
  const storage = options.storage || memoryStorage();
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
  const cryptoObject = {
    subtle: webcrypto.subtle,
    getRandomValues: (view) => {
      for (let index = 0; index < view.length; index += 1) view[index] = (index + (options.seed || 0)) % 256;
      return view;
    }
  };
  function fetchStub(url, init) {
    fetchCalls.push({ url: String(url), body: init && init.body ? String(init.body) : '' });
    if (options.fetchThrows) throw new Error('network is forbidden in this suite');
    const bodyBytes = RECORDED_BYTES;
    return Promise.resolve({
      ok: true,
      headers: { get: (name) => (name === 'X-FIF-Response-SHA256' ? RECORDED_SHA : '') },
      arrayBuffer: () => Promise.resolve(bodyBytes.buffer.slice(bodyBytes.byteOffset, bodyBytes.byteOffset + bodyBytes.byteLength)),
      json: () => Promise.resolve(JSON.parse(RECORDED_BODY))
    });
  }
  function XhrStub() { xhrCount.count += 1; throw new Error('XMLHttpRequest is forbidden in this suite'); }
  const windowObject = {
    location,
    localStorage: storage,
    crypto: cryptoObject,
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
    fetch: fetchStub,
    XMLHttpRequest: XhrStub,
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
    setTimeout: (fn) => fn(),
    // The page calls bare fetch/crypto/subtle — contextifying the sandbox
    // object makes these the page's globals, exactly like a browser window.
    fetch: fetchStub,
    XMLHttpRequest: XhrStub,
    crypto: cryptoObject,
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
  api.state.payload = PAGE_PAYLOAD;
  api.state.symbol = 'AAPL';
  api.state.access = 'open';
  api.state.health = {
    status: 'current',
    clocks: { broad_source_at: '2026-10-11T23:59:59Z', composed_state_at: '2026-10-11T23:59:59Z' },
    generation: { id: 'ffprods_' + 'a1b2c3d4'.repeat(8), admitted_at: '2026-10-10T04:00:00Z' }
  };
  return {
    api, nodes, windowListeners, pushes, replaces, location, storage,
    fetchCalls, xhrCount, window: windowObject
  };
}

function freshBriefcase(storage, seed) {
  // The context's transports THROW and count, so any network reach from the
  // store module fails the suite loudly instead of silently succeeding.
  const network = { fetches: 0, xhrs: 0 };
  const context = vm.createContext({
    window: {
      localStorage: storage,
      crypto: { getRandomValues: (view) => { for (let i = 0; i < view.length; i += 1) view[i] = (i + (seed || 0)) % 256; return view; } },
      fetch: () => { network.fetches += 1; throw new Error('network is forbidden'); },
      XMLHttpRequest: function () { network.xhrs += 1; throw new Error('network is forbidden'); }
    },
    console,
  });
  vm.runInContext(BRIEFCASE_SOURCE, context, { filename: 'fif_saved_briefcase.js' });
  const Briefcase = context.window.FifSavedBriefcase;
  Briefcase.__networkProbe = network;
  return Briefcase;
}

const STORE_KEY = 'mastermind.filing_forensics.saved_research.v1';

// vm realms give objects a foreign prototype, so node's deepStrictEqual
// rejects structurally identical values; JSON equality is realm-blind.
function sameJson(actual, expected) {
  assert.equal(JSON.stringify(actual), JSON.stringify(expected));
}

test('save -> reload (fresh module instance over the same storage) -> identical object', () => {
  const { api, storage } = harness();
  api.initSavedBriefcase();
  api.state.asOfDate = '2026-09-30';
  api.state.policy = 'latest_known_as_of';
  api.state.symbol = 'AAPL';
  const saved = api.performSavedSave('Apple pinned at September cutoff');
  assert.equal(saved.ok, true, saved.reason || 'save refused');
  const stored = JSON.parse(storage.rows.get(STORE_KEY));
  assert.equal(stored.contract, 'fundamental_forensics.saved_research.v1');
  assert.ok(!('inbox' in stored), 'no inbox key on the container');

  // Fresh module instance, same storage bytes: persistence is in the store.
  const Briefcase = freshBriefcase(storage, 0);
  const reopened = Briefcase.create({ now: () => '2026-10-12T00:00:00Z' });
  const listing = reopened.list();
  assert.equal(listing.length, 1);
  assert.equal(listing[0].id, saved.view.id);
  assert.equal(listing[0].available, true);
  const loaded = reopened.load(saved.view.id);
  assert.equal(loaded.ok, true);
  sameJson(loaded.view, saved.view);
});

test('fixture identity: the module output for fixed inputs equals the committed fixture bytes', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 2);
  const store = Briefcase.create({ now: () => '2026-10-12T00:00:00Z' });
  const pinned = fixtureContainer('saved_pinned.json').saved_views[0];
  const input = {
    name: pinned.name,
    issuer: pinned.issuer,
    request: pinned.request,
    peers: pinned.peers,
    view: pinned.view,
    pinned: pinned.pinned,
    saved_against: pinned.saved_against,
    evidence_refs: pinned.evidence_refs,
    watch: pinned.watch
  };
  const result = store.save(input);
  assert.equal(result.ok, true, result.reason || 'save refused');
  sameJson(result.view, pinned);

  const cohortBriefcase = freshBriefcase(memoryStorage(), 1);
  const committedCohort = fixtureContainer('saved_cohort.json').saved_views[0];
  const cohort = cohortBriefcase.create({ now: () => '2026-10-12T00:00:00Z' })
    .save({
      name: 'Apple vs mega-cap peers',
      issuer: pinned.issuer,
      // The committed cohort fixture's OWN request bytes — clocks included —
      // so the comparison below needs no clock substitution and nothing is
      // overwritten before being compared.
      request: JSON.parse(JSON.stringify(committedCohort.request)),
      peers: { cohort: 'cohort_2026q3_megacap', peer_metric: 'revenue', align: 'shift_labeled', peer_n: 5, peer_tol: 60 },
      view: { tab: 'peers', finding: null },
      pinned: false,
      saved_against: pinned.saved_against,
      evidence_refs: [],
      watch: { issuer: false }
    });
  assert.equal(cohort.ok, true, cohort.reason || 'save refused');
  // Assert BEFORE any assignment: the module's stored request IS the
  // committed fixture's request, byte for byte — then the whole object.
  sameJson(cohort.view.request, committedCohort.request);
  sameJson(cohort.view, committedCohort);
});

test('the page-built request for the pinned desk equals the committed fixture request', () => {
  const { api } = harness();
  api.initSavedBriefcase();
  api.state.asOfDate = '2026-09-30';
  api.state.policy = 'latest_known_as_of';
  const input = api.buildSavedViewInput('Apple pinned at September cutoff');
  const pinned = fixtureContainer('saved_pinned.json').saved_views[0];
  sameJson(input.request, pinned.request);
  assert.equal(input.pinned, true);
});

test('pinned restore re-POSTs the stored request bytes verbatim; digest header matches', async () => {
  const container = fixtureContainer('saved_pinned.json');
  const { api, fetchCalls, storage } = harness();
  storage.setItem(STORE_KEY, JSON.stringify(container));
  api.initSavedBriefcase();
  api.state.symbol = 'MSFT';
  const result = api.restoreSavedView(container.saved_views[0].id);
  assert.equal(result.ok, true, result.reason || 'restore refused');
  assert.equal(api.state.symbol, 'AAPL');
  assert.equal(api.state.asOfDate, '2026-09-30');
  assert.equal(api.state.tab, 'compare');
  // The financial POST rides a withAuth promise chain: settle it first.
  await untilFinancialSettled(api);

  const queryPosts = fetchCalls.filter((call) => call.url.indexOf('/api/forensics/v1/financial/query') >= 0);
  assert.ok(queryPosts.length >= 1, 'the financial query fired');
  const storedBytes = JSON.stringify(container.saved_views[0].request);
  const latestLeg = queryPosts.find((call) => {
    const body = JSON.parse(call.body);
    return body.policy.selection === 'latest_known_as_of';
  });
  assert.ok(latestLeg, 'the latest-known leg posted');
  assert.equal(latestLeg.body, storedBytes, 'posted bytes equal the stored request bytes');
  // The stub header matches the served body; the page verified it internally
  // (a mismatch would have surfaced as a 503, not phase 'ready').
  assert.equal(RECORDED_SHA, createHash('sha256').update(RECORDED_BYTES).digest('hex'));
  assert.equal(api.state.financial.phase, 'ready', 'the pinned restore query completed');
  assert.equal(api.state.financial.responseSha256, RECORDED_SHA);
});

test('latest restore recomputes clocks from health the way P2 already does', async () => {
  const container = fixtureContainer('saved_latest.json');
  const drive = harness();
  drive.storage.setItem(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  const result = drive.api.restoreSavedView(container.saved_views[0].id);
  assert.equal(result.ok, true, result.reason || 'restore refused');
  // The latest fixture opens the radar tab, which issues no financial POST —
  // drive the compare tab the way a reader would and check the rebuilt clocks
  // against the health clocks (policyClocks() Latest branch).
  drive.api.setTab('compare', false);
  await untilFinancialSettled(drive.api);
  const latestLeg = drive.fetchCalls
    .filter((call) => call.url.indexOf('/api/forensics/v1/financial/query') >= 0)
    .map((call) => JSON.parse(call.body))
    .find((body) => body.policy.selection === 'latest_known_as_of');
  assert.ok(latestLeg, 'the latest-known leg posted');
  assert.equal(latestLeg.policy.source_snapshot_at, '2026-10-11T23:59:59Z');
  assert.equal(latestLeg.policy.recorded_at, '2026-10-11T23:59:59Z');
});

test('direct link restores subject, policy, cutoff and cohort through P2\'s URL reader', () => {
  const container = fixtureContainer('saved_cohort.json');
  const first = harness();
  first.storage.setItem(STORE_KEY, JSON.stringify(container));
  first.api.initSavedBriefcase();
  first.api.restoreSavedView(container.saved_views[0].id);
  const permalink = first.pushes.at(-1);
  assert.match(permalink, /symbol=AAPL/);
  assert.match(permalink, /tab=peers/);
  assert.match(permalink, /cohort=cohort_2026q3_megacap/);
  assert.match(permalink, /peer_metric=revenue/);
  assert.match(permalink, /align=shift_labeled/);
  assert.match(permalink, /peer_n=5/);
  assert.match(permalink, /peer_tol=60/);

  const second = harness();
  second.location.search = permalink.replace(/^[^?]*/, '');
  const frame = second.api.readUrlParams();
  assert.equal(frame.symbol, 'AAPL');
  assert.equal(frame.tab, 'peers');
  assert.equal(frame.cohort, 'cohort_2026q3_megacap');
  assert.equal(frame.peerMetric, 'revenue');
  assert.equal(frame.align, 'shift_labeled');
  assert.equal(frame.peerN, 5);
  assert.equal(frame.peerTol, 60);
  second.api.applyUrlState(true);
  assert.equal(second.api.state.symbol, 'AAPL');
  assert.equal(second.api.state.cohortId, 'cohort_2026q3_megacap');
  assert.equal(second.api.state.peerAlign, 'shift_labeled');
  assert.equal(second.api.state.peerN, 5);
  assert.equal(second.api.state.peerTol, 60);
  assert.equal(second.api.state.tab, 'peers');

  const pinned = harness();
  pinned.storage.setItem(STORE_KEY, JSON.stringify(fixtureContainer('saved_pinned.json')));
  pinned.api.initSavedBriefcase();
  pinned.api.restoreSavedView(fixtureContainer('saved_pinned.json').saved_views[0].id);
  const pinnedLink = pinned.pushes.at(-1);
  assert.match(pinnedLink, /as_of=2026-09-30/);
  const third = harness();
  third.location.search = pinnedLink.replace(/^[^?]*/, '');
  third.api.applyUrlState(true);
  assert.equal(third.api.state.symbol, 'AAPL');
  assert.equal(third.api.state.asOfDate, '2026-09-30');
  assert.equal(third.api.state.policy, 'latest_known_as_of');
  assert.equal(third.api.state.tab, 'compare');
});

test('Back (popstate) restores the previous frame and clears the restored view', () => {
  const container = fixtureContainer('saved_cohort.json');
  const { api, windowListeners, location, storage } = harness();
  storage.setItem(STORE_KEY, JSON.stringify(container));
  api.initSavedBriefcase();
  api.bindEvents();
  api.state.symbol = 'MSFT';
  const result = api.restoreSavedView(container.saved_views[0].id);
  assert.equal(result.ok, true);
  assert.equal(api.state.savedActiveId, container.saved_views[0].id);

  location.search = '?symbol=MSFT&tab=radar';
  (windowListeners.popstate || []).forEach((handler) => handler());
  assert.equal(api.state.symbol, 'MSFT');
  assert.equal(api.state.cohortId, '');
  assert.equal(api.state.tab, 'radar');
  assert.equal(api.state.savedActiveId, '', 'the restored view no longer describes this frame');
});

test('every T1 refusal reason refuses the load with its exact reason and stays listed + deletable', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  function refusal(name, mutate, expected) {
    const row = JSON.parse(JSON.stringify(base));
    row.id = 'refusal' + Math.abs(name.length);
    mutate(row);
    const storage = memoryStorage([[STORE_KEY, JSON.stringify({ contract: 'fundamental_forensics.saved_research.v1', saved_views: [row] })]]);
    const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    const listing = store.list();
    assert.equal(listing.length, 1, name + ' stays listed');
    assert.equal(listing[0].available, false, name + ' listed unavailable');
    assert.equal(listing[0].reason, expected, name + ' lists its exact reason');
    const loaded = store.load(row.id);
    assert.equal(loaded.ok, false, name + ' refuses the load');
    assert.equal(loaded.reason, expected, name + ' refuses with the exact reason');
    const removed = store.remove(row.id);
    sameJson(removed, { ok: true, deleted: true });
    assert.equal(store.list().length, 0, name + ' deletable');
  }
  refusal('schema', (row) => { row.schema = 'fundamental_forensics.saved_research.v9'; }, 'schema');
  refusal('request_contract', (row) => { row.request_contract = 'fundamental_forensics.financial_query_request/v2'; }, 'request_contract');
  refusal('request_schema', (row) => { row.request.schema = 'fundamental_forensics.financial_query_request/v2'; }, 'request_schema');
  refusal('request_root', (row) => { row.request.extra_key = 'x'; }, 'request_root');
  refusal('request_canonical (period missing label)', (row) => { delete row.request.periods[0].label; }, 'request_canonical');
  refusal('request_canonical (extra policy key)', (row) => { row.request.policy.extra = 'x'; }, 'request_canonical');
  refusal('pinned_type', (row) => { row.pinned = 'true'; }, 'pinned_type');
  refusal('peers', (row) => { row.peers.align = 'sometimes'; }, 'peers');
  refusal('view', (row) => { row.view.tab = 'statements2'; }, 'view');
  // A pinned view with an empty clock names the clock: the pinned_cutoffs
  // check runs BEFORE the deep canonical check, so this reason stays
  // reachable and specific.
  refusal('pinned_cutoffs', (row) => {
    row.pinned = true;
    row.request.policy.source_snapshot_at = '';
  }, 'pinned_cutoffs');
  // The same empty clock on an UNPINNED view is a canonical-form drift.
  refusal('request_canonical (unpinned, empty clock)', (row) => {
    row.pinned = false;
    row.request.policy.source_snapshot_at = '';
  }, 'request_canonical');
});

test('a container whose own bytes drift goes READ-ONLY and is never overwritten (GovRev discipline)', () => {
  const variants = {
    'unparseable bytes': '{"contract":',
    'contract v2': JSON.stringify({ contract: 'fundamental_forensics.saved_research.v2', saved_views: [] }),
    'saved_views not an array': JSON.stringify({ contract: 'fundamental_forensics.saved_research.v1', saved_views: {} }),
    'extra root key': JSON.stringify({ contract: 'fundamental_forensics.saved_research.v1', saved_views: [], inbox: [] })
  };
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const input = (row) => ({
    name: row.name, issuer: row.issuer, request: row.request, peers: row.peers,
    view: row.view, pinned: row.pinned, saved_against: row.saved_against,
    evidence_refs: row.evidence_refs, watch: row.watch
  });
  for (const [name, bytes] of Object.entries(variants)) {
    const storage = memoryStorage([[STORE_KEY, bytes]]);
    const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    assert.equal(store.readOnly(), true, name + ': the store is read-only');
    assert.equal(store.list().length, 0, name + ': lists nothing');
    const saved = store.save(input(base));
    assert.equal(saved.ok, false, name + ': the save attempt refuses');
    assert.equal(saved.reason, 'unavailable', name + ': exact reason unavailable');
    assert.equal(storage.getItem(STORE_KEY), bytes, name + ': stored bytes are byte-identical afterwards');
  }
});

test('the store makes zero network calls and writes only its own key, signed in and signed out', () => {
  for (const signedIn of [true, false]) {
    const label = signedIn ? 'signed in' : 'signed out';
    const storage = memoryStorage();
    const Briefcase = freshBriefcase(storage, 3);
    const store = Briefcase.create({ storage, now: () => '2026-10-12T00:00:00Z' });
    const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
    const saved = store.save({
      name: base.name, issuer: base.issuer, request: base.request, peers: base.peers,
      view: base.view, pinned: base.pinned, saved_against: base.saved_against,
      evidence_refs: base.evidence_refs, watch: base.watch
    });
    assert.equal(saved.ok, true, label + ': the save succeeded');
    store.list();
    store.load(saved.view.id);
    store.update(saved.view.id, { name: 'Renamed' });
    store.remove(saved.view.id);
    Briefcase.toInvestigationManifestV2(saved.view);
    Briefcase.fromInvestigationManifestV2(Briefcase.toInvestigationManifestV2(base));
    // Signed in or signed out makes no difference to a module that owns no
    // transport: the throwing fetch/XHR stubs were never reached. EVERY
    // iteration asserts the whole contract, named for its iteration.
    assert.equal(Briefcase.__networkProbe.fetches, 0, label + ': zero fetches');
    assert.equal(Briefcase.__networkProbe.xhrs, 0, label + ': zero XMLHttpRequests');
    assert.equal(/fetch\(|XMLHttpRequest|navigator\.sendBeacon/.test(BRIEFCASE_SOURCE), false,
      label + ': the store module contains no transport calls');
    assert.deepEqual([...new Set(storage.written)], [STORE_KEY], label + ': only its own key is written');
  }
});

test('restore of a drifted view shows the plain unavailable state, never a crash', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  base.request_contract = 'fundamental_forensics.financial_query_request/v0';
  const drive = harness();
  drive.api.state.symbol = 'MSFT';
  drive.storage.setItem(STORE_KEY, JSON.stringify({
    contract: 'fundamental_forensics.saved_research.v1', saved_views: [base]
  }));
  drive.api.initSavedBriefcase();
  const result = drive.api.restoreSavedView(base.id);
  assert.equal(result.ok, false);
  assert.equal(result.reason, 'request_contract');
  assert.equal(drive.api.state.savedRefusal, 'request_contract');
  assert.equal(drive.api.state.symbol, 'MSFT', 'the desk was not navigated');
  drive.api.renderSavedUI();
  assert.equal(drive.nodes['ff-saved-notice'].hidden, false);
  assert.match(drive.nodes['ff-saved-notice'].innerHTML, /Saved view unavailable/);
});

test('an issuer that left the run refuses with the unavailable state', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  base.issuer.ticker = 'NOPE1';
  const drive = harness();
  drive.storage.setItem(STORE_KEY, JSON.stringify({
    contract: 'fundamental_forensics.saved_research.v1', saved_views: [base]
  }));
  drive.api.initSavedBriefcase();
  const result = drive.api.restoreSavedView(base.id);
  assert.equal(result.ok, false);
  assert.equal(result.reason, 'issuer');
  assert.equal(drive.api.state.savedRefusal, 'issuer');
});

// ── X2-s r1 NEGATIVE suite (one test per refusal, exact reason strings) ───

function containerBytes(row) {
  return JSON.stringify({ contract: 'fundamental_forensics.saved_research.v1', saved_views: [row] });
}

// X2-s r2 (R2-1b/R2-2): a seeded multi-row container — distinct ids so one
// tab's removal and the other's update address different rows.
function seedBytes(rows) {
  return JSON.stringify({ contract: 'fundamental_forensics.saved_research.v1', saved_views: rows });
}

function clonedRow(row, id, name) {
  const clone = JSON.parse(JSON.stringify(row));
  clone.id = id;
  if (name) clone.name = name;
  return clone;
}

test('NEGATIVE 1: a malformed inner request refuses request_canonical exactly', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  delete base.request.periods[0].label;
  const storage = memoryStorage([[STORE_KEY, containerBytes(base)]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const listing = store.list();
  assert.equal(listing.length, 1);
  assert.equal(listing[0].available, false);
  assert.equal(listing[0].reason, 'request_canonical');
  const loaded = store.load(base.id);
  assert.equal(loaded.ok, false);
  assert.equal(loaded.reason, 'request_canonical');
});

test('NEGATIVE 2: a pinned view whose policy.selection is outside the enum refuses request_canonical exactly', () => {
  const base = fixtureContainer('saved_pinned.json').saved_views[0];
  base.request.policy.selection = 'sometimes';
  const storage = memoryStorage([[STORE_KEY, containerBytes(base)]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const loaded = store.load(base.id);
  assert.equal(loaded.ok, false);
  assert.equal(loaded.reason, 'request_canonical');
});

test('NEGATIVE 3: a ticker that resolves to a different entity refuses issuer and leaves the desk untouched', () => {
  const base = fixtureContainer('saved_pinned.json').saved_views[0];
  base.request.entity_id = 'ISS:US-XNAS-MSFT';
  const drive = harness();
  drive.storage.setItem(STORE_KEY, containerBytes(base));
  drive.api.initSavedBriefcase();
  drive.api.state.symbol = 'MSFT';
  const before = {
    symbol: drive.api.state.symbol,
    policy: drive.api.state.policy,
    asOfDate: drive.api.state.asOfDate,
    cohortId: drive.api.state.cohortId,
    peerMetric: drive.api.state.peerMetric,
    peerAlign: drive.api.state.peerAlign,
    peerN: drive.api.state.peerN,
    peerTol: drive.api.state.peerTol,
    pinnedRequest: drive.api.state.pinnedRequest,
    tab: drive.api.state.tab
  };
  const result = drive.api.restoreSavedView(base.id);
  assert.equal(result.ok, false);
  assert.equal(result.reason, 'issuer');
  assert.equal(drive.api.state.savedRefusal, 'issuer');
  const after = {
    symbol: drive.api.state.symbol,
    policy: drive.api.state.policy,
    asOfDate: drive.api.state.asOfDate,
    cohortId: drive.api.state.cohortId,
    peerMetric: drive.api.state.peerMetric,
    peerAlign: drive.api.state.peerAlign,
    peerN: drive.api.state.peerN,
    peerTol: drive.api.state.peerTol,
    pinnedRequest: drive.api.state.pinnedRequest,
    tab: drive.api.state.tab
  };
  assert.deepEqual(after, before, 'the desk state is exactly its pre-restore snapshot');
  assert.equal(drive.nodes['ff-saved-notice'].hidden, false, 'the unavailable notice shows');
  assert.match(drive.nodes['ff-saved-notice'].innerHTML, /not covered by the current run/);
  // A refused restore is never the active view: no pinned badge, no
  // newer-generation chip; the refused row stays deletable.
  assert.equal(drive.nodes['ff-saved-badge'].hidden, true, 'no pinned badge for a refused restore');
  assert.equal(drive.api.savedGenerationStale(), null, 'no newer-generation chip for a refused restore');
  assert.equal(drive.nodes['ff-saved-delete'].hidden, false, 'the refused row stays deletable');
});

test('NEGATIVE 4: update() on a refused row refuses with that row\'s reason and never changes stored bytes', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  base.pinned = 'true';
  const bytes = containerBytes(base);
  const storage = memoryStorage([[STORE_KEY, bytes]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const updated = store.update(base.id, { name: 'Renamed anyway' });
  assert.equal(updated.ok, false);
  assert.equal(updated.reason, 'pinned_type');
  assert.equal(storage.getItem(STORE_KEY), bytes, 'the stored bytes are byte-identical');
  assert.equal(store.list()[0].name, base.name, 'the in-memory row was not rewritten either');
});

test('NEGATIVE 5: a failed persistence returns storage, rolls back, and a later good save works', () => {
  const storage = onceFailingStorage();
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const first = store.save({
    name: base.name, issuer: base.issuer, request: base.request, peers: base.peers,
    view: base.view, pinned: base.pinned, saved_against: base.saved_against,
    evidence_refs: base.evidence_refs, watch: base.watch
  });
  assert.equal(first.ok, false);
  assert.equal(first.reason, 'storage');
  assert.equal(store.list().length, 0, 'the in-memory list is unchanged (the pushed row was dropped)');
  storage.repair();
  const second = store.save({
    name: base.name, issuer: base.issuer, request: base.request, peers: base.peers,
    view: base.view, pinned: base.pinned, saved_against: base.saved_against,
    evidence_refs: base.evidence_refs, watch: base.watch
  });
  assert.equal(second.ok, true, second.reason || 'the later good save works');
  assert.equal(store.list().length, 1);
});

test('NEGATIVE 6: a drifted container refuses a save attempt with unavailable and stays byte-identical', () => {
  const bytes = JSON.stringify({
    contract: 'government_procurement_local_state.v1',
    saved_views: [{ schema: 'fundamental_forensics.saved_research.v1', id: 'x' }]
  });
  const storage = memoryStorage([[STORE_KEY, bytes]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const saved = store.save({
    name: base.name, issuer: base.issuer, request: base.request, peers: base.peers,
    view: base.view, pinned: base.pinned, saved_against: base.saved_against,
    evidence_refs: base.evidence_refs, watch: base.watch
  });
  assert.equal(saved.ok, false);
  assert.equal(saved.reason, 'unavailable');
  assert.equal(storage.getItem(STORE_KEY), bytes, 'the drifted bytes are preserved byte-identically');
});

// ── X2-s r2 R2-1: cross-tab lost update (ONE shared storage, TWO tabs that
// were both created BEFORE either writes — the store must re-read the stored
// bytes at the start of every operation) ────────────────────────────────────

test('T-R2-1a: two tabs: A saves then B saves and both rows survive', () => {
  const shared = memoryStorage();
  const A = freshBriefcase(shared, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const B = freshBriefcase(shared, 7).create({ now: () => '2026-10-12T00:00:00Z' });
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const input = (name) => ({
    name: name, issuer: base.issuer, request: base.request, peers: base.peers,
    view: base.view, pinned: base.pinned, saved_against: base.saved_against,
    evidence_refs: base.evidence_refs, watch: base.watch
  });
  const first = A.save(input('Saved in tab A'));
  assert.equal(first.ok, true, first.reason || 'A save refused');
  const second = B.save(input('Saved in tab B'));
  assert.equal(second.ok, true, second.reason || 'B save refused');
  const both = [first.view.id, second.view.id].sort();
  assert.notEqual(first.view.id, second.view.id, 'distinct seeds give distinct ids');
  const stored = JSON.parse(shared.rows.get(STORE_KEY));
  assert.equal(stored.saved_views.length, 2, 'both rows survive in the stored bytes');
  sameJson(stored.saved_views.map((row) => row.id).sort(), both);
  sameJson(A.list().map((entry) => entry.id).sort(), both, 'tab A lists both rows');
  sameJson(B.list().map((entry) => entry.id).sort(), both, 'tab B lists both rows');
});

test('T-R2-1b: two tabs: a row A removed stays removed when B later updates another row', () => {
  const row1 = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const row2 = clonedRow(row1, 'SECONDROWFROMSEED000000', 'Second row');
  const shared = memoryStorage([[STORE_KEY, seedBytes([row1, row2])]]);
  const A = freshBriefcase(shared, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const B = freshBriefcase(shared, 7).create({ now: () => '2026-10-12T00:00:00Z' });
  const removed = A.remove(row1.id);
  sameJson(removed, { ok: true, deleted: true });
  const updated = B.update(row2.id, { name: 'renamed in B' });
  assert.equal(updated.ok, true, updated.reason || 'B update refused');
  const stored = JSON.parse(shared.rows.get(STORE_KEY));
  assert.equal(stored.saved_views.length, 1, 'exactly one row survives in the stored bytes');
  assert.equal(stored.saved_views[0].id, row2.id);
  assert.equal(stored.saved_views[0].name, 'renamed in B');
  assert.equal(B.load(row1.id).reason, 'missing', 'the removed row does not resurrect for B');
});

test('T-R2-1c: two tabs: drift written after B was created is seen by B', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const input = {
    name: base.name, issuer: base.issuer, request: base.request, peers: base.peers,
    view: base.view, pinned: base.pinned, saved_against: base.saved_against,
    evidence_refs: base.evidence_refs, watch: base.watch
  };
  const shared = memoryStorage();
  const B = freshBriefcase(shared, 7).create({ now: () => '2026-10-12T00:00:00Z' });
  // (i) a schema-drifted row lands in the shared bytes AFTER B was created.
  const drifted = clonedRow(base, 'DRIFTEDROWSEENBYTAB0000');
  drifted.schema = 'fundamental_forensics.saved_research.v0';
  shared.setItem(STORE_KEY, seedBytes([drifted]));
  const listed = B.list();
  assert.equal(listed.length, 1);
  assert.equal(listed[0].id, drifted.id);
  assert.equal(listed[0].available, false);
  assert.equal(listed[0].reason, 'schema');
  const saved = B.save(input);
  assert.equal(saved.ok, true, saved.reason || 'B save refused');
  const afterSave = JSON.parse(shared.rows.get(STORE_KEY));
  assert.equal(afterSave.saved_views.length, 2);
  const kept = afterSave.saved_views.find((row) => row.id === drifted.id);
  assert.ok(kept, 'the drifted row is still in the stored bytes');
  sameJson(kept, drifted);
  // (ii) a drifted container contract turns B read-only mid-session.
  const driftedContainer = JSON.stringify({
    contract: 'fundamental_forensics.saved_research.v0',
    saved_views: [{ schema: 'fundamental_forensics.saved_research.v1', id: 'x' }]
  });
  shared.setItem(STORE_KEY, driftedContainer);
  assert.equal(B.readOnly(), true);
  sameJson(B.list(), []);
  const refused = B.save(input);
  assert.equal(refused.ok, false);
  assert.equal(refused.reason, 'unavailable');
  assert.equal(shared.rows.get(STORE_KEY), driftedContainer,
    'the drifted container bytes are byte-identical to what was written');
});

test('T-R2-1d: a throwing getItem makes the store read-only and never writes', () => {
  const writes = { count: 0 };
  const storage = {
    getItem: () => { throw new Error('storage refused'); },
    setItem: () => { writes.count += 1; },
    removeItem: () => {},
  };
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  assert.equal(store.readOnly(), true);
  sameJson(store.list(), []);
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const saved = store.save({
    name: base.name, issuer: base.issuer, request: base.request, peers: base.peers,
    view: base.view, pinned: base.pinned, saved_against: base.saved_against,
    evidence_refs: base.evidence_refs, watch: base.watch
  });
  assert.equal(saved.ok, false);
  assert.equal(saved.reason, 'unavailable');
  assert.equal(writes.count, 0, 'no setItem call ever happens');
});

// ── X2-s r2 R2-2: rollback of update/remove over real seed rows. Once R2-1
// lands every operation re-reads storage, so the in-memory rollback is no
// longer independently observable through the public API; these pin the
// observable contract and MUST fail against a store with the per-operation
// read reverted AND the rollback lines deleted (see the lane's falsifiers). ──

test('NEGATIVE 7: a failed update returns storage, changes nothing, and a later good write keeps the old name', () => {
  const row1 = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const row2 = clonedRow(row1, 'SECONDROWFROMSEED000000', 'Second row');
  const seed = seedBytes([row1, row2]);
  const storage = onceFailingStorageWith([[STORE_KEY, seed]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const failed = store.update(row1.id, { name: 'should not stick' });
  assert.equal(failed.ok, false);
  assert.equal(failed.reason, 'storage');
  assert.equal(store.load(row1.id).view.name, row1.name, 'the OLD name survives the failed update');
  assert.equal(storage.getItem(STORE_KEY), seed, 'the stored bytes are byte-identical to the seed');
  storage.repair();
  const good = store.update(row2.id, { name: 'other' });
  assert.equal(good.ok, true, good.reason || 'the later good write works');
  const stored = JSON.parse(storage.getItem(STORE_KEY));
  assert.equal(stored.saved_views.find((row) => row.id === row1.id).name, row1.name,
    'id1 keeps its OLD name in the stored bytes');
  assert.equal(stored.saved_views.find((row) => row.id === row2.id).name, 'other');
});

test('NEGATIVE 8: a failed remove returns storage, removes nothing, and a later good write keeps the row', () => {
  const row1 = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const row2 = clonedRow(row1, 'SECONDROWFROMSEED000000', 'Second row');
  const seed = seedBytes([row1, row2]);
  const storage = onceFailingStorageWith([[STORE_KEY, seed]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const failed = store.remove(row1.id);
  assert.equal(failed.ok, false);
  assert.equal(failed.reason, 'storage');
  assert.equal(store.load(row1.id).ok, true, 'the row is still loadable');
  sameJson(store.list().map((entry) => entry.id).sort(), [row1.id, row2.id].sort(),
    'both rows stay listed');
  assert.equal(storage.getItem(STORE_KEY), seed, 'the stored bytes are byte-identical to the seed');
  storage.repair();
  const good = store.update(row2.id, { name: 'other' });
  assert.equal(good.ok, true, good.reason || 'the later good write works');
  const stored = JSON.parse(storage.getItem(STORE_KEY));
  assert.ok(stored.saved_views.some((row) => row.id === row1.id),
    'the row B failed to remove is still in the stored bytes after a later good write');
});

// ── X2-s r1 page-side repairs ─────────────────────────────────────────────

test('a pinned view saved under as_reported posts every leg from the stored bytes, latest leg included', async () => {
  const container = fixtureContainer('saved_pinned.json');
  const row = container.saved_views[0];
  row.request.policy.selection = 'as_reported';
  const { api, fetchCalls, storage } = harness();
  storage.setItem(STORE_KEY, JSON.stringify(container));
  api.initSavedBriefcase();
  api.state.symbol = 'MSFT';
  const result = api.restoreSavedView(row.id);
  assert.equal(result.ok, true, result.reason || 'restore refused');
  await untilFinancialSettled(api);
  const queryPosts = fetchCalls.filter((call) => call.url.indexOf('/api/forensics/v1/financial/query') >= 0);
  const selections = queryPosts.map((call) => JSON.parse(call.body).policy.selection);
  assert.deepEqual(selections, ['as_reported', 'latest_known_as_of', 'latest_restated'],
    'the three legs post exactly as the code orders them');
  const stored = row.request;
  queryPosts.forEach((call, index) => {
    const body = JSON.parse(call.body);
    const expected = JSON.parse(JSON.stringify(stored));
    expected.policy.selection = selections[index];
    assert.deepEqual(body, expected,
      'leg ' + selections[index] + ' is the stored request with only policy.selection changed');
  });
});

test('with ?policy=as_reported and no pinned view the export body keeps the desk selection', async () => {
  const drive = harness();
  drive.location.search = '?symbol=AAPL&policy=as_reported';
  drive.api.applyUrlState(true);
  drive.api.setTab('compare', false);
  await untilFinancialSettled(drive.api);
  assert.equal(drive.api.state.policy, 'as_reported');
  assert.equal(drive.api.state.financial.phase, 'ready');
  const body = drive.api.exportQueryBody();
  assert.equal(body.policy.selection, 'as_reported',
    'the export body follows the desk policy, not the forced latest leg');
});

test('a missing view shows the missing copy, never the contract copy', () => {
  const drive = harness();
  drive.api.initSavedBriefcase();
  const result = drive.api.restoreSavedView('GONEFROMTHISDEVICE00');
  assert.equal(result.ok, false);
  assert.equal(result.reason, 'missing');
  assert.equal(drive.api.state.savedRefusal, 'missing');
  assert.equal(drive.nodes['ff-saved-notice'].hidden, false);
  assert.match(drive.nodes['ff-saved-notice'].innerHTML, /no longer on this device/);
  assert.doesNotMatch(drive.nodes['ff-saved-notice'].innerHTML, /older contract/);
});

test('an unreadable store pauses saving and shows the store notice', () => {
  const drive = harness();
  drive.storage.setItem(STORE_KEY, '{"contract":');
  drive.api.initSavedBriefcase();
  drive.api.renderSavedUI();
  assert.equal(drive.nodes['ff-saved-save'].disabled, true, 'Save stays disabled');
  assert.equal(drive.nodes['ff-saved-rename'].hidden, true, 'Rename stays hidden');
  assert.equal(drive.nodes['ff-saved-delete'].hidden, true, 'Delete stays hidden');
  assert.equal(drive.nodes['ff-saved-notice'].hidden, false);
  assert.match(drive.nodes['ff-saved-notice'].innerHTML, /could not be read/);
  assert.equal(drive.storage.getItem(STORE_KEY), '{"contract":', 'the unreadable bytes are untouched');
});

test('a failed persistence shows the write-failure notice through the save path', () => {
  const drive = harness({ storage: failingStorage() });
  drive.api.initSavedBriefcase();
  const result = drive.api.performSavedSave('Apple pinned at September cutoff');
  assert.equal(result.ok, false);
  assert.equal(result.reason, 'storage');
  assert.equal(drive.api.state.savedStoreError, true);
  assert.equal(drive.api.state.savedRefusal, '');
  assert.equal(drive.nodes['ff-saved-notice'].hidden, false);
  assert.match(drive.nodes['ff-saved-notice'].innerHTML, /did not save this change/);
  assert.ok(drive.nodes['ff-saved-notice'].innerHTML.indexOf('浏览器未保存此更改，其他内容未变。') >= 0,
    'the bilingual pair carries the Chinese copy');
  assert.doesNotMatch(drive.nodes['ff-saved-notice'].innerHTML, /Saving is paused here/);
});

test('T-R2-4b: a later successful save hides the write-failure notice and clears savedStoreError', () => {
  const storage = onceFailingStorage();
  const drive = harness({ storage });
  drive.api.initSavedBriefcase();
  const first = drive.api.performSavedSave('Apple pinned at September cutoff');
  assert.equal(first.ok, false);
  assert.equal(first.reason, 'storage');
  assert.equal(drive.api.state.savedStoreError, true);
  storage.repair();
  const second = drive.api.performSavedSave('Apple pinned at September cutoff');
  assert.equal(second.ok, true, second.reason || 'the repaired save works');
  assert.equal(drive.api.state.savedStoreError, false);
  assert.equal(drive.nodes['ff-saved-notice'].hidden, true, 'the write-failure notice is hidden again');
});

test('the saved list offers a choice when populated and says empty only when empty', () => {
  const drive = harness();
  drive.storage.setItem(STORE_KEY, JSON.stringify(fixtureContainer('saved_latest.json')));
  drive.api.initSavedBriefcase();
  drive.api.renderSavedUI();
  const populated = drive.nodes['ff-saved-select'].innerHTML;
  assert.match(populated, /<option value="">Choose a saved view<\/option>/);
  assert.doesNotMatch(populated, /No saved views yet/);

  const empty = harness();
  empty.api.initSavedBriefcase();
  empty.api.renderSavedUI();
  assert.match(empty.nodes['ff-saved-select'].innerHTML, /<option value="">No saved views yet<\/option>/);
});

test('the unavailable notice carries a title element (MINOR-5 shape)', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  base.request_contract = 'fundamental_forensics.financial_query_request/v0';
  const drive = harness();
  drive.storage.setItem(STORE_KEY, containerBytes(base));
  drive.api.initSavedBriefcase();
  drive.api.restoreSavedView(base.id);
  drive.api.renderSavedUI();
  const html = drive.nodes['ff-saved-notice'].innerHTML;
  assert.match(html, /^<span class="ff-notice-icon" aria-hidden="true">i<\/span><div><strong>/);
  assert.match(html, /<\/strong><div>/);
  assert.match(html, /older contract/);
});

// ── X2-s r2 R2-3: a refused view can never become active (a write failure
// is tracked in state.savedStoreError and never overwrites a refusal) ──────

test('T-R2-3a: a write failure never turns an issuer-refused view active', () => {
  const base = fixtureContainer('saved_pinned.json').saved_views[0];
  base.request.entity_id = 'ISS:US-XNAS-MSFT';
  const seed = containerBytes(base);
  const drive = harness({ storage: failingStorage([[STORE_KEY, seed]]) });
  drive.api.initSavedBriefcase();
  drive.api.state.symbol = 'MSFT';
  const restored = drive.api.restoreSavedView(base.id);
  assert.equal(restored.ok, false);
  assert.equal(restored.reason, 'issuer');
  assert.equal(drive.api.state.savedRefusal, 'issuer');
  const failed = drive.api.performSavedSave('x');
  assert.equal(failed.ok, false);
  assert.equal(failed.reason, 'storage');
  assert.equal(drive.api.state.savedRefusal, 'issuer', 'the issuer refusal survives the failed save');
  assert.equal(drive.api.state.savedStoreError, true);
  assert.equal(drive.nodes['ff-saved-badge'].hidden, true, 'the refused view shows no badge');
  assert.equal(drive.nodes['ff-saved-rename'].hidden, true, 'the refused view offers no Rename');
  // An explicit render/backfill pass must not write: the backfill only acts
  // on an ACTIVE view, and a refused view is never active.
  drive.api.backfillSavedAgainst();
  drive.api.renderSavedUI();
  assert.equal(drive.storage.getItem(STORE_KEY), seed, 'the stored bytes are byte-identical to the seed');
  const renamed = drive.api.savedRenameActive('y');
  assert.equal(renamed.ok, false);
  assert.equal(renamed.reason, 'storage');
  assert.equal(drive.api.state.savedRefusal, 'issuer', 'the refusal survives a failed rename');
  const deleted = drive.api.savedDeleteActive();
  assert.equal(deleted.ok, false);
  assert.equal(deleted.reason, 'storage');
  assert.equal(drive.api.state.savedRefusal, 'issuer', 'the refusal survives a failed delete');
  assert.equal(drive.storage.getItem(STORE_KEY), seed, 'the stored bytes never changed');
});

test('T-R2-3b: the refusal reason survives a failed save for a contract-refused row', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  base.request_contract = 'fundamental_forensics.financial_query_request/v0';
  const drive = harness({ storage: failingStorage([[STORE_KEY, containerBytes(base)]]) });
  drive.api.initSavedBriefcase();
  const restored = drive.api.restoreSavedView(base.id);
  assert.equal(restored.ok, false);
  assert.equal(restored.reason, 'request_contract');
  const failed = drive.api.performSavedSave('x');
  assert.equal(failed.ok, false);
  assert.equal(failed.reason, 'storage');
  assert.equal(drive.api.state.savedRefusal, 'request_contract');
  assert.equal(drive.api.state.savedStoreError, true);
  assert.equal(drive.nodes['ff-saved-badge'].hidden, true, 'the refused view shows no badge');
});

test('T-R2-3c: a refused restore clears a previously pinned request', () => {
  const pinned = fixtureContainer('saved_pinned.json').saved_views[0];
  const mismatched = JSON.parse(JSON.stringify(pinned));
  mismatched.id = 'ISSUERMISMATCHROW00000';
  mismatched.request.entity_id = 'ISS:US-XNAS-MSFT';
  const drive = harness();
  drive.storage.setItem(STORE_KEY, seedBytes([pinned, mismatched]));
  drive.api.initSavedBriefcase();
  const restored = drive.api.restoreSavedView(pinned.id);
  assert.equal(restored.ok, true, restored.reason || 'the pinned fixture view restores');
  assert.ok(drive.api.state.pinnedRequest, 'a pinned restore keeps a pinned request');
  const refused = drive.api.restoreSavedView(mismatched.id);
  assert.equal(refused.ok, false);
  assert.equal(refused.reason, 'issuer');
  assert.equal(drive.api.state.pinnedRequest, null, 'the refused restore cleared the pinned request');
});

test('id-problem rows stay listed under row:<index>, refuse load, and are removable by that key', () => {
  const good = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const noId = JSON.parse(JSON.stringify(good));
  delete noId.id;
  const dup = JSON.parse(JSON.stringify(good));
  const rows = [good, noId, dup];
  const storage = memoryStorage([[STORE_KEY, JSON.stringify({
    contract: 'fundamental_forensics.saved_research.v1', saved_views: rows
  })]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const listing = store.list();
  assert.equal(listing.length, 3, 'every row stays listed — nothing is dropped');
  assert.equal(listing[0].id, good.id);
  assert.equal(listing[0].available, true);
  assert.equal(listing[1].id, 'row:1');
  assert.equal(listing[1].available, false);
  assert.equal(listing[1].reason, 'id');
  assert.equal(listing[2].id, 'row:2');
  assert.equal(listing[2].available, false);
  assert.equal(listing[2].reason, 'id');
  assert.equal(store.load('row:1').reason, 'id');
  assert.equal(store.load('row:2').reason, 'id');
  assert.equal(store.update('row:2', { name: 'Renamed anyway' }).reason, 'id');
  // A real id acts on the FIRST row carrying it.
  const byId = store.load(good.id);
  assert.equal(byId.ok, true);
  sameJson(byId.view, good);
  const removed = store.remove('row:2');
  sameJson(removed, { ok: true, deleted: true });
  assert.equal(store.list().map((entry) => entry.id).join(','), good.id + ',row:1',
    'the duplicate row is gone; renumbered addresses follow the surviving rows');
});

test('the evidence harness seed loads rows 1-2 and refuses the drift row as schema', () => {
  const container = fixtureContainer('evidence_briefcase_seed.json');
  const storage = memoryStorage([[STORE_KEY, JSON.stringify(container)]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const listing = store.list();
  assert.equal(listing.length, 3, 'all three rows stay listed');
  assert.equal(listing[0].id, 'CDEFGHIJKLMNOPQRSTUVWX');
  assert.equal(listing[0].available, true, 'row 1 (saved_pinned verbatim) is available');
  assert.equal(listing[1].id, 'DEFGHIJKLMNOPQRSTUVWXY');
  assert.equal(listing[1].available, true, 'row 2 (saved_latest verbatim) is available');
  assert.equal(listing[2].id, 'EFGHIJKLMNOPQRSTUVWXYZ');
  assert.equal(listing[2].available, false, 'the drift row is unavailable');
  assert.equal(listing[2].reason, 'schema');
  const pinned = store.load('CDEFGHIJKLMNOPQRSTUVWX');
  const latest = store.load('DEFGHIJKLMNOPQRSTUVWXY');
  assert.equal(pinned.ok, true, 'row 1 loads');
  assert.equal(latest.ok, true, 'row 2 loads');
  sameJson(pinned.view, fixtureContainer('saved_pinned.json').saved_views[0]);
  sameJson(latest.view, fixtureContainer('saved_latest.json').saved_views[0]);
  const drift = store.load('EFGHIJKLMNOPQRSTUVWXYZ');
  assert.equal(drift.ok, false);
  assert.equal(drift.reason, 'schema');
});

test('the A->B manifest mapping round-trips every fixture losslessly', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  for (const name of [
    'saved_single_issuer.json', 'saved_cohort.json', 'saved_pinned.json',
    'saved_latest.json', 'saved_with_evidence.json', 'saved_with_finding.json'
  ]) {
    const view = fixtureContainer(name).saved_views[0];
    const manifest = Briefcase.toInvestigationManifestV2(view);
    assert.ok(manifest, name + ' maps');
    assert.equal(manifest.schema, 'investigation_manifest.v2');
    assert.equal(manifest.intent.subjects[0].kind, 'issuer');
    assert.equal(manifest.intent.subjects[0].object_id, view.issuer.entity_id);
    sameJson(Briefcase.fromInvestigationManifestV2(manifest), view);
    if (view.pinned) {
      assert.equal(manifest.intent.research_as_of, view.request.policy.source_snapshot_at.slice(0, 10));
    } else {
      assert.equal(manifest.intent.research_as_of, undefined);
    }
    // Manifest-v2 reference law: pinned refs carry version_ref, follow_head
    // refs carry neither version_ref nor fingerprint.
    manifest.evidence_refs.forEach((ref) => {
      if (ref.mode === 'pinned') assert.ok(ref.version_ref, 'pinned refs name their version');
      else assert.equal('version_ref' in ref || 'fingerprint' in ref, false, 'follow_head refs carry no version');
    });
    // No metric value and no stray number outside the audited allow-list
    // (peers.peer_n, peers.peer_tol, evidence_refs[].source_span inside the
    // verbatim carrier).
    walkNumbers(manifest, '$', (path) => {
      assert.match(path, /^\$\.fif_saved_research\.(peers\.peer_n|peers\.peer_tol|evidence_refs\[\d+\]\.source_span\[\d+\])$/,
        name + ' carries an unaudited number at ' + path);
    });
  }
});

function walkNumbers(value, path, visit) {
  if (typeof value === 'number') { visit(path); return; }
  if (Array.isArray(value)) {
    value.forEach((entry, index) => walkNumbers(entry, path + '[' + index + ']', visit));
    return;
  }
  if (value && typeof value === 'object') {
    Object.keys(value).forEach((key) => walkNumbers(value[key], path + '.' + key, visit));
  }
}

test('fromInvestigationManifestV2 refuses non-manifest and carrier-less shapes', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  assert.equal(Briefcase.fromInvestigationManifestV2({ schema: 'investigation_manifest.v1' }), null);
  assert.equal(Briefcase.fromInvestigationManifestV2(null), null);
  const manifest = Briefcase.toInvestigationManifestV2(fixtureContainer('saved_pinned.json').saved_views[0]);
  delete manifest.fif_saved_research;
  assert.equal(Briefcase.fromInvestigationManifestV2(manifest), null);
});

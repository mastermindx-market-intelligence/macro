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
// The health world the harness seeds (state.health AND the health stub below
// answer with exactly these clocks/generation, so the page's real health flow
// and the direct injection describe one world).
const SEEDED_CLOCKS = { broad_source_at: '2026-10-11T23:59:59Z', composed_state_at: '2026-10-11T23:59:59Z' };
const SEEDED_GENERATION = { id: 'ffprods_' + 'a1b2c3d4'.repeat(8), admitted_at: '2026-10-10T04:00:00Z' };

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
    // PF r1 (R1): the compare chain now consumes the health FETCH answer, so
    // the stub answers health with the same clocks/generation the harness
    // seeds below (previously the generic envelope raced the direct
    // injection and only lost after the request bytes were built).
    if (String(url).indexOf('/api/forensics/health') >= 0) {
      return Promise.resolve({
        ok: true,
        headers: {
          get: (name) => (name === 'X-FIF-Dataset-Generation-Id' ? SEEDED_GENERATION.id
            : name === 'X-FIF-Dataset-Admitted-At' ? SEEDED_GENERATION.admitted_at : '')
        },
        json: () => Promise.resolve({ status: 'current', clocks: SEEDED_CLOCKS })
      });
    }
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
    clocks: SEEDED_CLOCKS,
    generation: { id: SEEDED_GENERATION.id, admitted_at: SEEDED_GENERATION.admitted_at }
  };
  // PF r1 (R1): the compare chain waits for the selected issuer's accepted
  // health answer; tests that never run loadHealth still describe a world
  // where AAPL's answer already landed (the seed above).
  api.state.healthAnswer = { entity_id: 'ISS:US-XNAS-AAPL', seq: 0, ok: true, pointer: '' };
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

test('id-problem rows stay listed under row:<index>:<fingerprint>, refuse load, and are removable by that key', () => {
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
  assert.match(listing[1].id, /^row:1:[0-9a-f]{8}$/, 'the id-less row is addressed by index + fingerprint');
  assert.equal(listing[1].available, false);
  assert.equal(listing[1].reason, 'id');
  assert.match(listing[2].id, /^row:2:[0-9a-f]{8}$/, 'the duplicate-id row is addressed by index + fingerprint');
  assert.equal(listing[2].available, false);
  assert.equal(listing[2].reason, 'id');
  assert.equal(store.load(listing[1].id).reason, 'id');
  assert.equal(store.load(listing[2].id).reason, 'id');
  assert.equal(store.update(listing[2].id, { name: 'Renamed anyway' }).reason, 'id');
  // A real id acts on the FIRST row carrying it.
  const byId = store.load(good.id);
  assert.equal(byId.ok, true);
  sameJson(byId.view, good);
  const removed = store.remove(listing[2].id);
  sameJson(removed, { ok: true, deleted: true });
  sameJson(store.list().map((entry) => entry.id), [good.id, listing[1].id],
    'the duplicate row is gone; the surviving rows keep their listing ids');
});

// ── X2-b r2 MINOR 1: an index-only row address can point at a DIFFERENT row
// after another tab writes. The address now carries a fingerprint of the
// row's bytes, so it keeps naming the row the user saw. ─────────────────────

function junkRows() {
  const good = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const junk1 = JSON.parse(JSON.stringify(good));
  delete junk1.id;
  const junk2 = JSON.parse(JSON.stringify(good));
  delete junk2.id;
  junk2.name = 'A different name entirely';
  return { good, junk1, junk2 };
}

// The test's own FNV-1a copy: a listing id for an id-problem row must be
// exactly 'row:<index>:' + this fingerprint of the row's bytes.
function fnv1aHex(value) {
  let serialized = JSON.stringify(value);
  if (serialized === undefined) serialized = 'undefined';
  let hash = 0x811c9dc5;
  for (let index = 0; index < serialized.length; index += 1) {
    hash = Math.imul(hash ^ serialized.charCodeAt(index), 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, '0');
}

test('T-X2B-1a: a stale row address deletes the row the user saw, never its new neighbour', () => {
  const { good, junk1, junk2 } = junkRows();
  const shared = memoryStorage([[STORE_KEY, seedBytes([good, junk1, junk2])]]);
  const A = freshBriefcase(shared, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const B = freshBriefcase(shared, 7).create({ now: () => '2026-10-12T00:00:00Z' });
  const addr = B.list()[1].id;
  assert.match(addr, /^row:1:[0-9a-f]{8}$/, 'tab B addresses junk1 by index + fingerprint');
  // Tab A deletes the lawful row, so index 1 now holds junk2.
  sameJson(A.remove(good.id), { ok: true, deleted: true });
  // The stale address must still delete junk1 (the row the user saw), never
  // its new neighbour junk2.
  sameJson(B.remove(addr), { ok: true, deleted: true });
  const stored = JSON.parse(shared.rows.get(STORE_KEY));
  sameJson(stored.saved_views, [junk2], 'junk1 was deleted and junk2 survived');
});

test('T-X2B-1b: a row address whose row is gone deletes nothing', () => {
  const { good, junk1, junk2 } = junkRows();
  const shared = memoryStorage([[STORE_KEY, seedBytes([good, junk1, junk2])]]);
  const A = freshBriefcase(shared, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const B = freshBriefcase(shared, 7).create({ now: () => '2026-10-12T00:00:00Z' });
  const addr = B.list()[1].id;
  // Tab A deletes junk1 through ITS OWN listing address for the same bytes.
  sameJson(A.remove(A.list()[1].id), { ok: true, deleted: true });
  const before = shared.rows.get(STORE_KEY);
  sameJson(B.remove(addr), { ok: true, deleted: false });
  assert.equal(shared.rows.get(STORE_KEY), before, 'the stored bytes are unchanged by the stale remove');
});

test('T-X2B-1c: a bare legacy row:<index> address is inert', () => {
  const { good, junk1, junk2 } = junkRows();
  const shared = memoryStorage([[STORE_KEY, seedBytes([good, junk1, junk2])]]);
  const store = freshBriefcase(shared, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const before = shared.rows.get(STORE_KEY);
  assert.equal(store.load('row:1').reason, 'missing');
  assert.equal(store.update('row:1', { name: 'x' }).reason, 'missing');
  sameJson(store.remove('row:1'), { ok: true, deleted: false });
  assert.equal(shared.rows.get(STORE_KEY), before, 'the stored bytes are unchanged');
});

test('T-X2B-1d: the row: id namespace is reserved', () => {
  const good = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const reserved = JSON.parse(JSON.stringify(good));
  reserved.id = 'row:0:00000000';
  const storage = memoryStorage([[STORE_KEY, seedBytes([reserved])]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const listing = store.list();
  assert.equal(listing.length, 1);
  assert.equal(listing[0].available, false);
  assert.equal(listing[0].reason, 'id');
  const fingerprint = fnv1aHex(reserved);
  assert.notEqual(fingerprint, '00000000', 'guard: the fixture bytes do not hash to the reserved literal');
  assert.equal(listing[0].id, 'row:0:' + fingerprint,
    'the listing id is the index plus the row\'s own fingerprint, never its literal stored id');
  // A literal id inside the reserved namespace never names the row by id:
  // 'row:0:00000000' does not carry the row's real fingerprint, so it
  // resolves to no address at all.
  assert.equal(store.load(reserved.id).reason, 'missing');
});

test('T-X2B-1e: two tabs derive the same row address for the same bytes', () => {
  const { good, junk1, junk2 } = junkRows();
  const shared = memoryStorage([[STORE_KEY, seedBytes([good, junk1, junk2])]]);
  const A = freshBriefcase(shared, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const B = freshBriefcase(shared, 7).create({ now: () => '2026-10-12T00:00:00Z' });
  const a = A.list();
  const b = B.list();
  assert.equal(a.length, b.length);
  for (let index = 0; index < a.length; index += 1) {
    assert.equal(a[index].id, b[index].id, 'row ' + index + ' carries the same address in both tabs');
  }
});

// ── X2-b r2 MINOR 2: a view deleted in ANOTHER tab after this tab restored
// it must turn into its own refusal on the next read — the missing notice
// shows, no pinned badge renders, no pinned bytes are served. ──────────────

function restoredPinnedDrive() {
  const container = fixtureContainer('saved_pinned.json');
  const row = container.saved_views[0];
  const drive = harness();
  drive.storage.setItem(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  const restored = drive.api.restoreSavedView(row.id);
  assert.equal(restored.ok, true, restored.reason || 'the pinned fixture view restores');
  return { drive, row };
}

test('T-X2B-2a: an active pinned view deleted in another tab shows the missing notice and stops serving pinned bytes', () => {
  const { drive, row } = restoredPinnedDrive();
  assert.equal(drive.nodes['ff-saved-badge'].hidden, false, 'the pinned badge is shown after the restore');
  assert.ok(drive.api.state.pinnedRequest, 'the pinned request bytes are held');
  // Tab A: a SECOND briefcase instance on the same storage deletes the view.
  const tabA = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  sameJson(tabA.remove(row.id), { ok: true, deleted: true });
  drive.api.renderSavedUI();
  assert.equal(drive.api.state.savedRefusal, 'missing');
  assert.equal(drive.api.state.pinnedRequest, null);
  assert.equal(drive.nodes['ff-saved-notice'].hidden, false, 'the missing notice shows');
  assert.match(drive.nodes['ff-saved-notice'].innerHTML, /no longer on this device/);
  assert.equal(drive.nodes['ff-saved-badge'].hidden, true, 'the badge is hidden');
  assert.equal(drive.nodes['ff-saved-rename'].hidden, true, 'the rename button is hidden');
  assert.equal(drive.api.activePinnedRequest(), null, 'no pinned bytes are served');
});

test('T-X2B-2b: activePinnedRequest notices the deletion even before any render', () => {
  const { drive, row } = restoredPinnedDrive();
  const tabA = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  sameJson(tabA.remove(row.id), { ok: true, deleted: true });
  // No renderSavedUI() first: the pinned-read path itself must reconcile.
  assert.equal(drive.api.activePinnedRequest(), null, 'no pinned bytes are served');
  assert.equal(drive.api.state.savedRefusal, 'missing');
  assert.equal(drive.api.state.pinnedRequest, null);
});

test('T-X2B-2c: a present active view is never refused by the reconcile', () => {
  const { drive, row } = restoredPinnedDrive();
  const before = drive.storage.getItem(STORE_KEY);
  drive.api.renderSavedUI();
  assert.equal(drive.api.state.savedRefusal, '', 'a present view is never refused');
  assert.equal(drive.nodes['ff-saved-badge'].hidden, false, 'the badge is shown');
  const request = drive.api.activePinnedRequest();
  assert.ok(request, 'the pinned request is still served');
  sameJson(request, row.request);
  assert.equal(drive.storage.getItem(STORE_KEY), before, 'the stored bytes are unchanged by the two calls');
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

// ── X2-b+c r2 MAJOR-1: an edit in another tab must REFUSE the active view,
// never keep serving stale pinned bytes behind a "latest" badge ─────────────

test('T-MAJOR1-a: another tab unpinning the active view refuses it as changed', () => {
  const { drive, row } = restoredPinnedDrive();
  assert.equal(drive.nodes['ff-saved-badge'].hidden, false, 'the pinned badge is shown after the restore');
  assert.ok(drive.api.state.pinnedRequest, 'the pinned request bytes are held');
  const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  assert.equal(tabB.update(row.id, { pinned: false }).ok, true, 'tab B unpins the view');
  const afterEdit = drive.storage.getItem(STORE_KEY);
  drive.api.renderSavedUI();
  assert.equal(drive.api.state.savedRefusal, 'changed', 'the pinned-to-latest edit refuses as changed');
  assert.equal(drive.api.state.pinnedRequest, null, 'the stale pinned bytes are dropped');
  assert.equal(drive.api.activePinnedRequest(), null, 'no pinned bytes are served');
  assert.equal(drive.nodes['ff-saved-badge'].hidden, true, 'the badge never says latest');
  assert.equal(drive.nodes['ff-saved-notice'].hidden, false, 'the refusal notice shows');
  assert.match(drive.nodes['ff-saved-notice'].innerHTML, /changed in another tab/);
  assert.match(drive.nodes['ff-saved-notice'].innerHTML, /Reopen it to continue/);
  assert.ok(drive.nodes['ff-saved-notice'].innerHTML.indexOf('此已保存视图已在另一个标签页中更改。请重新打开以继续。') >= 0,
    'the bilingual pair carries the Chinese copy');
  assert.equal(drive.storage.getItem(STORE_KEY), afterEdit, 'the render itself wrote nothing');
});

test('T-MAJOR1-b: another tab changing the stored request refuses it as changed, even before any render', () => {
  const { drive, row } = restoredPinnedDrive();
  const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const revised = JSON.parse(JSON.stringify(row.request));
  revised.policy.source_snapshot_at = '2026-10-11T23:59:59Z';
  revised.policy.recorded_at = '2026-10-11T23:59:59Z';
  assert.equal(tabB.update(row.id, { request: revised }).ok, true, 'tab B re-cuts the stored request');
  // No renderSavedUI() first: the pinned-read path itself reconciles.
  assert.equal(drive.api.activePinnedRequest(), null, 'the changed request bytes are not served');
  assert.equal(drive.api.state.savedRefusal, 'changed');
  assert.equal(drive.api.state.pinnedRequest, null);
  drive.api.renderSavedUI();
  assert.equal(drive.nodes['ff-saved-badge'].hidden, true, 'no badge renders for the refused view');
});

test('T-MAJOR1-c: another tab pinning a latest view refuses it as changed too', () => {
  const container = fixtureContainer('saved_latest.json');
  const row = container.saved_views[0];
  const drive = harness();
  drive.storage.setItem(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  assert.equal(drive.api.restoreSavedView(row.id).ok, true, 'the latest fixture view restores');
  assert.equal(drive.api.state.pinnedRequest, null, 'a latest view serves no pinned bytes');
  const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  assert.equal(tabB.update(row.id, { pinned: true }).ok, true, 'tab B pins the view');
  drive.api.renderSavedUI();
  assert.equal(drive.api.state.savedRefusal, 'changed', 'the latest-to-pinned edit refuses as changed');
  assert.equal(drive.nodes['ff-saved-badge'].hidden, true, 'the badge never claims latest for a now-pinned view');
});

// ── X2-b+c r2 MINOR-1: a read-only store stops serving pinned bytes ─────────

test('T-MINOR1: a read-only store refuses the active view as store and serves no pinned bytes', () => {
  const { drive } = restoredPinnedDrive();
  assert.ok(drive.api.state.pinnedRequest, 'the pinned request bytes are held');
  // The container's own bytes go unreadable behind this tab's back.
  drive.storage.setItem(STORE_KEY, '{"contract":');
  assert.equal(drive.api.activePinnedRequest(), null, 'no pinned bytes are served from a read-only store');
  assert.equal(drive.api.state.savedRefusal, 'store', 'the existing store refusal is set');
  assert.equal(drive.api.state.pinnedRequest, null);
  drive.api.renderSavedUI();
  assert.match(drive.nodes['ff-saved-notice'].innerHTML, /could not be read/);
});

// ── X2-b+c r2 MINOR-2: grapheme-safe free text, never-cut identifiers ───────

test('T-MINOR2-name: the repro name saves with its emoji whole and still exports', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const store = Briefcase.create({ now: () => '2026-10-12T00:00:00Z' });
  const view = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const emoji = String.fromCodePoint(0x1f600);
  const reproName = 'a'.repeat(119) + emoji; // 120 code points, 121 UTF-16 units
  const saved = store.save(Object.assign({}, view, { name: reproName }));
  assert.equal(saved.ok, true, saved.reason || 'the repro name saves');
  assert.equal(saved.view.name, reproName, 'the name keeps the whole emoji — no lone surrogate is minted');
  assert.equal(Array.from(saved.view.name).length, 120);
  const emitted = Briefcase.emitInvestigationManifestV2(saved.view);
  assert.ok(emitted.ok, 'the saved view exports');
  assert.equal(emitted.manifest.intent.title, reproName);

  // The page's own save path stores the same exportable name.
  const drive = harness();
  drive.api.initSavedBriefcase();
  drive.api.state.asOfDate = '2026-09-30';
  drive.api.state.policy = 'latest_known_as_of';
  const result = drive.api.performSavedSave(reproName);
  assert.equal(result.ok, true, result.reason || 'the page saves the repro name');
  assert.ok(Briefcase.emitInvestigationManifestV2(result.view).ok, 'the page-saved view exports');
});

test('T-MINOR2-ids: identifiers are never cut — over-limit or lone-surrogate ids refuse and nothing is stored', () => {
  const lone = String.fromCharCode(0xd800);
  const view = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const refuseCase = (label, patch, reason) => {
    const storage = memoryStorage();
    const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    const refused = store.save(Object.assign({}, view, patch));
    assert.equal(refused.ok, false, label + ' refuses');
    assert.equal(refused.reason, reason, label + ' uses ' + reason);
    assert.equal(store.list().length, 0, label + ': nothing is stored');
    assert.equal(storage.getItem(STORE_KEY), null, label + ': no bytes were written');
  };
  refuseCase('a 161-code-point entity_id', {
    issuer: { entity_id: 'I'.repeat(161), cik: view.issuer.cik, ticker: view.issuer.ticker }
  }, 'text_too_long');
  refuseCase('a lone-surrogate entity_id', {
    issuer: { entity_id: 'ISS:' + lone, cik: view.issuer.cik, ticker: view.issuer.ticker }
  }, 'invalid_unicode');
  refuseCase('a 129-char occurrence_id', {
    evidence_refs: [{ accession: 'A', occurrence_id: 'o'.repeat(129), source_span: [0, 1] }]
  }, 'text_too_long');
  refuseCase('a 65-char accession', {
    evidence_refs: [{ accession: 'a'.repeat(65), occurrence_id: 'o', source_span: [0, 1] }]
  }, 'text_too_long');
  refuseCase('a lone-surrogate occurrence_id', {
    evidence_refs: [{ accession: 'A', occurrence_id: 'o' + lone, source_span: [0, 1] }]
  }, 'invalid_unicode');
  refuseCase('a name that already contains a lone surrogate', {
    name: 'x' + lone + 'y'
  }, 'invalid_unicode');
  // Accepted: the identifier limits keep storing verbatim at their bounds.
  const store = freshBriefcase(memoryStorage(), 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const saved = store.save(Object.assign({}, view, {
    issuer: { entity_id: 'I'.repeat(160), cik: view.issuer.cik, ticker: view.issuer.ticker },
    evidence_refs: [{ accession: 'a'.repeat(64), occurrence_id: 'o'.repeat(128), source_span: [0, 1] }]
  }));
  assert.equal(saved.ok, true, saved.reason || 'the at-limit ids save');
  assert.equal(saved.view.issuer.entity_id, 'I'.repeat(160));
  assert.equal(saved.view.evidence_refs[0].occurrence_id, 'o'.repeat(128));
  assert.equal(saved.view.evidence_refs[0].accession, 'a'.repeat(64));
});

test('T-MINOR2-update: rename cuts at a grapheme boundary and a lone-surrogate rename refuses', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const store = Briefcase.create({ now: () => '2026-10-12T00:00:00Z' });
  const view = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const saved = store.save(Object.assign({}, view));
  assert.equal(saved.ok, true, saved.reason || 'the base view saves');
  const emoji = String.fromCodePoint(0x1f600);
  const renamed = store.update(saved.view.id, { name: 'a'.repeat(119) + emoji });
  assert.equal(renamed.ok, true, renamed.reason || 'the repro rename works');
  assert.equal(renamed.view.name, 'a'.repeat(119) + emoji, 'the whole emoji survives the rename');
  assert.ok(Briefcase.emitInvestigationManifestV2(renamed.view).ok, 'the renamed view exports');
  const refused = store.update(saved.view.id, { name: 'x' + String.fromCharCode(0xd800) });
  assert.equal(refused.ok, false);
  assert.equal(refused.reason, 'invalid_unicode');
  assert.equal(store.load(saved.view.id).view.name, 'a'.repeat(119) + emoji, 'the stored name is unchanged');
});

// ── X2-b+c r2 NIT-3: the duplicate-seen map must survive __proto__ ids ──────

test('T-NIT3: two rows with id __proto__ re-key the second like any duplicate, and remove pins down', () => {
  const good = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const first = clonedRow(good, '__proto__', 'proto first');
  const second = clonedRow(good, '__proto__', 'proto second');
  const storage = memoryStorage([[STORE_KEY, seedBytes([first, second])]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const listing = store.list();
  assert.equal(listing.length, 2);
  assert.equal(listing[0].id, '__proto__', 'the first __proto__ row keeps its id');
  assert.equal(listing[0].available, true);
  assert.match(listing[1].id, /^row:1:[0-9a-f]{8}$/,
    'the second __proto__ row is re-keyed like an ordinary duplicate');
  assert.equal(listing[1].available, false);
  assert.equal(listing[1].reason, 'id');
  // An ordinary duplicate shows exactly the same shape.
  const dupStorage = memoryStorage([[STORE_KEY,
    seedBytes([clonedRow(good, 'dup', 'dup first'), clonedRow(good, 'dup', 'dup second')])]]);
  const dupListing = freshBriefcase(dupStorage, 0).create({ now: () => '2026-10-12T00:00:00Z' }).list();
  assert.equal(dupListing[0].id, 'dup');
  assert.match(dupListing[1].id, /^row:1:[0-9a-f]{8}$/, 'an ordinary duplicate is re-keyed the same way');
  // remove('__proto__') deletes the FIRST row; the survivor is then keyed by id.
  const removed = store.remove('__proto__');
  sameJson(removed, { ok: true, deleted: true });
  sameJson(store.list().map((entry) => entry.id), ['__proto__'],
    'the surviving row is now the first __proto__ row, keyed by id');
  assert.equal(store.list()[0].available, true);
});

// ── X2-b+c r2 NIT-4: leading-zero indexes are refused, and a 32-bit
// fingerprint never names a row on its own — full canonical bytes decide ────

function idLessRow(name) {
  const row = JSON.parse(JSON.stringify(fixtureContainer('saved_single_issuer.json').saved_views[0]));
  delete row.id;
  row.name = name;
  return row;
}

test('T-NIT4-ambiguous: a 32-bit fingerprint collision never names the wrong row', () => {
  // These two names were found by a birthday search over random names: their
  // id-less rows collide in 32-bit FNV-1a while differing in bytes. The
  // suite's own fnv1aHex guard re-proves the collision.
  const a = idLessRow('xwoucicfayo');
  const b = idLessRow('xbtihxnaogo');
  assert.equal(fnv1aHex(a), fnv1aHex(b), 'guard: the rows collide in the 32-bit fingerprint');
  assert.equal(fnv1aHex(a), '5ef27944');
  assert.notEqual(JSON.stringify(a), JSON.stringify(b), 'guard: the rows differ in bytes');
  const storage = memoryStorage([[STORE_KEY, seedBytes([a, b])]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const before = storage.getItem(STORE_KEY);
  const listing = store.list();
  assert.match(listing[0].id, /^row:0:[0-9a-f]{8}$/);
  assert.equal(listing[0].id.split(':')[2], listing[1].id.split(':')[2],
    'both collision rows address under the same fingerprint');
  // The fingerprint alone is ambiguous — two different byte shapes carry it —
  // so the address resolves to nothing rather than the wrong row.
  assert.equal(store.load('row:0:' + fnv1aHex(a)).reason, 'missing');
  sameJson(store.remove('row:0:' + fnv1aHex(a)), { ok: true, deleted: false });
  assert.equal(storage.getItem(STORE_KEY), before, 'nothing was deleted');
});

test('T-NIT4-identical: byte-identical rows under one fingerprint stay addressable', () => {
  const a = idLessRow('same bytes twice');
  const b = JSON.parse(JSON.stringify(a));
  const storage = memoryStorage([[STORE_KEY, seedBytes([a, b])]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const addr = store.list()[0].id;
  assert.match(addr, /^row:0:[0-9a-f]{8}$/);
  // One canonical byte shape carries the fingerprint, so the address names
  // it unambiguously (either row is the same bytes).
  sameJson(store.remove(addr), { ok: true, deleted: true });
  sameJson(store.list().map((entry) => entry.id), [addr],
    'the surviving identical row keeps the same address');
});

test('T-NIT4-index: a row:01:<fp> address with a leading-zero index is refused', () => {
  const { good, junk1, junk2 } = junkRows();
  const storage = memoryStorage([[STORE_KEY, seedBytes([good, junk1, junk2])]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const before = storage.getItem(STORE_KEY);
  const addr = store.list()[1].id; // row:1:<fp of junk1>
  assert.match(addr, /^row:1:[0-9a-f]{8}$/);
  const zeroPadded = 'row:01:' + addr.split(':')[2];
  assert.equal(zeroPadded.indexOf('row:01:'), 0);
  assert.equal(store.load(zeroPadded).reason, 'missing');
  assert.equal(store.update(zeroPadded, { name: 'x' }).reason, 'missing');
  sameJson(store.remove(zeroPadded), { ok: true, deleted: false });
  assert.equal(storage.getItem(STORE_KEY), before, 'nothing was deleted by the malformed address');
});

// ── X2-b+c r2 NIT-2 (store side): a stored row with an unknown key refuses ──

test('T-NIT2-store: a stored row carrying an unknown key stays listed but refuses load as schema', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const row = JSON.parse(JSON.stringify(base));
  row.evil_extra = 1;
  const storage = memoryStorage([[STORE_KEY, containerBytes(row)]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const listing = store.list();
  assert.equal(listing.length, 1, 'the row stays listed');
  assert.equal(listing[0].available, false);
  assert.equal(listing[0].reason, 'schema');
  const loaded = store.load(row.id);
  assert.equal(loaded.ok, false);
  assert.equal(loaded.reason, 'schema');
  // The refused row stays deletable.
  sameJson(store.remove(row.id), { ok: true, deleted: true });
});

// ── X2-b+c r3 R3-1: values the UI can save must also export — the emitter's
// own checker runs at save/update time, with the emitter's code and path ─────

const CTRL = String.fromCharCode(1);
const NUL = String.fromCharCode(0);
const LONE = String.fromCharCode(0xd800);

function r3Store() {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  return { Briefcase: Briefcase, store: Briefcase.create({ now: () => '2026-10-12T00:00:00Z' }) };
}

test('T-R3-1-name-save: control characters and NUL in a name refuse at save with the emitter\'s code and path', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const cases = [
    ['\t', 'invalid_control'],
    ['\n', 'invalid_control'],
    [CTRL, 'invalid_control'],
    [NUL, 'unsupported_code_point']
  ];
  for (const [character, reason] of cases) {
    const { store } = r3Store();
    const refused = store.save(Object.assign({}, base, { name: 'a' + character + 'b' }));
    assert.equal(refused.ok, false, 'a name holding U+' + character.charCodeAt(0).toString(16).padStart(4, '0') + ' refuses');
    assert.equal(refused.reason, reason);
    assert.equal(refused.path, '$.intent.title', 'the refusal carries the emitter\'s own path');
    assert.equal(store.list().length, 0, 'nothing is stored');
  }
});

test('T-R3-1-name-update: the same refusals on rename, and the stored name never changes', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  for (const [character, reason] of [['\t', 'invalid_control'], [NUL, 'unsupported_code_point'], [CTRL, 'invalid_control']]) {
    const { store } = r3Store();
    const saved = store.save(Object.assign({}, base));
    assert.equal(saved.ok, true, saved.reason || 'the base view saves');
    const before = store.load(saved.view.id).view.name;
    const refused = store.update(saved.view.id, { name: 'a' + character + 'b' });
    assert.equal(refused.ok, false, 'a rename holding U+' + character.charCodeAt(0).toString(16).padStart(4, '0') + ' refuses');
    assert.equal(refused.reason, reason);
    assert.equal(refused.path, '$.intent.title');
    assert.equal(store.load(saved.view.id).view.name, before, 'the stored name is unchanged');
  }
});

test('T-R3-1-ids: an entity_id or occurrence_id carrying U+0001 refuses with the emitter\'s code and path', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const { store } = r3Store();
  const refusedIssuer = store.save(Object.assign({}, base, {
    issuer: { entity_id: 'ISS:x' + CTRL + 'y', cik: base.issuer.cik, ticker: base.issuer.ticker }
  }));
  assert.equal(refusedIssuer.ok, false);
  assert.equal(refusedIssuer.reason, 'invalid_control');
  assert.equal(refusedIssuer.path, '$.intent.subjects[0].object_id');
  const refusedOccurrence = store.save(Object.assign({}, base, {
    evidence_refs: [{ accession: 'A', occurrence_id: 'occ' + CTRL, source_span: [0, 1] }]
  }));
  assert.equal(refusedOccurrence.ok, false);
  assert.equal(refusedOccurrence.reason, 'invalid_control');
  assert.equal(refusedOccurrence.path, '$.evidence_refs[0].object_id');
  assert.equal(store.list().length, 0, 'nothing is stored');
});

test('T-R3-1-pinned-date: a pinned view whose snapshot cutoff is not a real calendar date refuses as the emitter would', () => {
  const base = fixtureContainer('saved_pinned.json').saved_views[0];
  for (const clock of ['garbage', '2026-13-01T00:00:00Z', '2026-02-30T00:00:00Z']) {
    const { store } = r3Store();
    const revised = JSON.parse(JSON.stringify(base.request));
    revised.policy.source_snapshot_at = clock;
    const refused = store.save(Object.assign({}, base, { request: revised }));
    assert.equal(refused.ok, false, 'the ' + clock + ' cutoff refuses');
    assert.equal(refused.reason, 'invalid_date');
    assert.equal(refused.path, '$.intent.research_as_of');
    assert.equal(store.list().length, 0, 'nothing is stored');
  }
  // The same gate holds on the update path, and the calendar fixture still saves.
  const { store } = r3Store();
  const saved = store.save(Object.assign({}, base));
  assert.equal(saved.ok, true, saved.reason || 'the calendar cutoff saves');
  const revised = JSON.parse(JSON.stringify(base.request));
  revised.policy.source_snapshot_at = '2026-02-30T00:00:00Z';
  const refusedUpdate = store.update(saved.view.id, { request: revised });
  assert.equal(refusedUpdate.ok, false, 'an impossible snapshot date refuses on update');
  assert.equal(refusedUpdate.reason, 'invalid_date');
  // recorded_at is never emitted: an impossible recorded date alone still saves.
  const revisedRecorded = JSON.parse(JSON.stringify(base.request));
  revisedRecorded.policy.recorded_at = '2026-02-30T00:00:00Z';
  assert.equal(store.update(saved.view.id, { request: revisedRecorded }).ok, true,
    'recorded_at is not projected, so it keeps the plain request law');
});

test('T-R3-1-duplicate-refs: two evidence refs the emitter would dedup refuse at save', () => {
  const base = fixtureContainer('saved_with_evidence.json').saved_views[0];
  const { store } = r3Store();
  const refused = store.save(Object.assign({}, base, {
    evidence_refs: [
      { accession: 'A', occurrence_id: 'same-occurrence', source_span: [0, 1] },
      { accession: 'A', occurrence_id: 'same-occurrence', source_span: [2, 3] }
    ]
  }));
  assert.equal(refused.ok, false, 'the repeated Terminal identity tuple refuses');
  assert.equal(refused.reason, 'duplicate_reference');
  assert.equal(refused.path, '$.evidence_refs[1]');
  assert.equal(store.list().length, 0, 'nothing is stored');
});

test('T-R3-1-surtex: a lone surrogate in a field the emitter never emits refuses and nothing is stored', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const cases = [
    [{ peers: { cohort: 'c' + LONE, peer_metric: null, align: 'exclude', peer_n: 3, peer_tol: 45 } }, 'peers.cohort'],
    [{ saved_against: { generation_id: 'g', admitted_at: 'a' + LONE, response_sha256: '' } }, 'saved_against.admitted_at'],
    [{ view: { tab: 'radar', finding: 'f' + LONE } }, 'view.finding']
  ];
  for (const [patch] of cases) {
    const { store } = r3Store();
    const refused = store.save(Object.assign({}, base, patch));
    assert.equal(refused.ok, false, 'a lone surrogate never stores');
    assert.equal(refused.reason, 'invalid_unicode');
    assert.equal(store.list().length, 0, 'nothing is stored');
  }
});

// The property the whole finding rides on: over the fixture inputs (every
// committed fixture crossed with the repro value variations), every value set
// the store ACCEPTS also exports through the emitter.
test('T-R3-1-property: every value set for which save returns ok also emits ok', () => {
  const Briefcase = freshBriefcase(memoryStorage(), 0);
  const emoji = String.fromCodePoint(0x1f600);
  const bases = [
    'saved_single_issuer.json', 'saved_cohort.json', 'saved_pinned.json',
    'saved_latest.json', 'saved_with_evidence.json', 'saved_with_finding.json'
  ].map((name) => fixtureContainer(name).saved_views[0]);
  const nameValues = ['ok name', 'a\tb', 'a' + CTRL + 'b', 'a' + NUL + 'b', 'x' + LONE + 'y',
    'a'.repeat(120), 'a'.repeat(121), 'a'.repeat(119) + emoji, ' padded ', ' '];
  const issuerValues = [
    { entity_id: 'ISS:US-XNAS-AAPL', cik: '0000320193', ticker: 'AAPL' },
    { entity_id: 'I'.repeat(160), cik: 'c'.repeat(32), ticker: 't'.repeat(32) },
    { entity_id: 'I'.repeat(161), cik: 'c'.repeat(33), ticker: 'AAPL' },
    { entity_id: 'e' + CTRL, cik: '0000320193', ticker: 'AAPL' },
    { entity_id: 'e' + LONE, cik: '0000320193', ticker: 'AAPL' },
    { entity_id: '', cik: '0000320193', ticker: 'AAPL' }
  ];
  const againstValues = [
    null,
    { generation_id: null, admitted_at: null, response_sha256: null },
    { generation_id: 'g'.repeat(128), admitted_at: 'a'.repeat(80), response_sha256: 'c9f2ab0451de6933ba7f1c0d4e5f60718293a4b5c6d7e8f9a1b2c3d4e5f60712' },
    { generation_id: 'g'.repeat(129), admitted_at: '', response_sha256: '' },
    { generation_id: 'g' + LONE, admitted_at: 'x', response_sha256: '' }
  ];
  const refValues = [
    [],
    [{ accession: 'A', occurrence_id: 'occ', source_span: [0, 1] }],
    [{ accession: 'a'.repeat(64), occurrence_id: 'o'.repeat(128), source_span: [0, 1] }],
    [{ accession: 'a'.repeat(65), occurrence_id: 'o', source_span: [0, 1] }],
    [{ accession: '', occurrence_id: '', source_span: [0, 1] }],
    [{ accession: 'A', occurrence_id: 'o' + CTRL, source_span: [0, 1] }],
    [{ accession: 'A', occurrence_id: 'occ', source_span: [0, 1] }, { accession: 'A', occurrence_id: 'occ', source_span: [2, 3] }],
    [{ accession: '', occurrence_id: 'fallback-id', source_span: [0, 1] }]
  ];
  const clockValues = ['2026-09-30T23:59:59Z', 'garbage', '2026-02-30T00:00:00Z'];
  let accepted = 0;
  let refused = 0;
  const check = (input, label) => {
    const store = Briefcase.create({ now: () => '2026-10-12T00:00:00Z', storage: memoryStorage() });
    const saved = store.save(input);
    if (!saved.ok) {
      refused += 1;
      assert.equal(store.list().length, 0, label + ': a refused save stores nothing');
      return;
    }
    accepted += 1;
    const emitted = Briefcase.emitInvestigationManifestV2(saved.view);
    assert.equal(emitted.ok, true,
      label + ': the stored view must export (got ' + emitted.reason + ' at ' + emitted.path + ')');
  };
  const vary = (base, patch) => {
    const input = Object.assign({}, base, patch);
    input.issuer = patch.issuer || base.issuer;
    input.request = patch.request || base.request;
    input.saved_against = 'saved_against' in patch ? patch.saved_against : base.saved_against;
    input.evidence_refs = 'evidence_refs' in patch ? patch.evidence_refs : base.evidence_refs;
    return input;
  };
  for (const base of bases) {
    const label = base.name.slice(0, 18);
    check(vary(base, {}), label + ' pristine');
    for (const name of nameValues) check(vary(base, { name: name }), label + ' name');
    for (const issuer of issuerValues) check(vary(base, { issuer: issuer }), label + ' issuer');
    for (const against of againstValues) check(vary(base, { saved_against: against }), label + ' saved_against');
    for (const refs of refValues) check(vary(base, { evidence_refs: refs }), label + ' refs');
    for (const clock of clockValues) {
      const revised = JSON.parse(JSON.stringify(base.request));
      revised.policy.source_snapshot_at = clock;
      check(vary(base, { request: revised }), label + ' clock ' + clock);
    }
    // Deterministic cross-sample (LCG): pairs of variations at a time.
    let state = 42;
    const next = (list) => list[(state = (state * 1103515245 + 12345) % 2147483648) % list.length];
    for (let round = 0; round < 40; round += 1) {
      check(vary(base, { name: next(nameValues), issuer: next(issuerValues) }), label + ' cross' + round);
      check(vary(base, { saved_against: next(againstValues), evidence_refs: next(refValues) }), label + ' cross-b' + round);
    }
  }
  // The update path keeps the same property for the one emitted field it can
  // change: every accepted rename still exports.
  const store = Briefcase.create({ now: () => '2026-10-12T00:00:00Z' });
  const saved = store.save(Object.assign({}, bases[0]));
  assert.equal(saved.ok, true, saved.reason || 'the base view saves');
  for (const name of nameValues) {
    const renamed = store.update(saved.view.id, { name: name });
    if (renamed.ok) {
      assert.ok(Briefcase.emitInvestigationManifestV2(renamed.view).ok,
        'the accepted rename ' + JSON.stringify(name) + ' must export');
    } else {
      assert.equal(renamed.reason === 'invalid_unicode' || renamed.reason === 'invalid_control' ||
        renamed.reason === 'unsupported_code_point' || renamed.reason === 'name', true,
        'the refused rename uses an emitter code or the name code');
    }
  }
  assert.ok(accepted > 100 && refused > 100, 'the sweep covered both sides (accepted ' + accepted + ', refused ' + refused + ')');
});

// ── X2-b+c r3 R3-2: identifiers are NEVER cut — over-limit or lone-surrogate
// ids refuse typed and nothing is stored ──────────────────────────────────────

test('T-R3-2-ids: generation_id, cik and ticker are never cut', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  const refuseCase = (label, patch, reason) => {
    const { store } = r3Store();
    const refused = store.save(Object.assign({}, base, patch));
    assert.equal(refused.ok, false, label + ' refuses');
    assert.equal(refused.reason, reason, label + ' uses ' + reason);
    assert.equal(store.list().length, 0, label + ': nothing is stored');
  };
  refuseCase('a 200-character generation_id', {
    saved_against: { generation_id: 'g'.repeat(200), admitted_at: '', response_sha256: '' }
  }, 'text_too_long');
  refuseCase('a 129-character generation_id', {
    saved_against: { generation_id: 'g'.repeat(129), admitted_at: '', response_sha256: '' }
  }, 'text_too_long');
  refuseCase('a 33-character cik', {
    issuer: { entity_id: base.issuer.entity_id, cik: 'c'.repeat(33), ticker: 'AAPL' }
  }, 'text_too_long');
  refuseCase('a 33-character ticker', {
    issuer: { entity_id: base.issuer.entity_id, cik: '0000320193', ticker: 't'.repeat(33) }
  }, 'text_too_long');
  // Values at the limit are accepted UNCHANGED — never trimmed to fit.
  const { store } = r3Store();
  const saved = store.save(Object.assign({}, base, {
    issuer: { entity_id: base.issuer.entity_id, cik: 'c'.repeat(32), ticker: 't'.repeat(32) },
    saved_against: { generation_id: 'g'.repeat(128), admitted_at: '', response_sha256: '' }
  }));
  assert.equal(saved.ok, true, saved.reason || 'the at-limit identifiers save');
  assert.equal(saved.view.issuer.cik, 'c'.repeat(32));
  assert.equal(saved.view.issuer.ticker, 't'.repeat(32));
  assert.equal(saved.view.saved_against.generation_id, 'g'.repeat(128));
  // The update path (the backfill shape) refuses the same over-limit id.
  const updated = store.update(saved.view.id, {
    saved_against: { generation_id: 'g'.repeat(129), admitted_at: '', response_sha256: '' }
  });
  assert.equal(updated.ok, false);
  assert.equal(updated.reason, 'text_too_long');
  assert.equal(store.load(saved.view.id).view.saved_against.generation_id, 'g'.repeat(128),
    'the stored generation_id is unchanged');
});

// ── X2-b+c r3 R3-3: no stale pinned export, no stale backfill ────────────────

async function restoredPinnedSettledDrive() {
  const { drive, row } = restoredPinnedDrive();
  await untilFinancialSettled(drive.api);
  assert.equal(drive.api.state.financial.phase, 'ready', 'the pinned fetch settled');
  assert.ok(drive.api.state.financial.queryBody, 'the pinned body is the ready query body');
  return { drive: drive, row: row };
}

test('T-R3-3-export: exportQueryBody returns null while a saved-view refusal is active', async () => {
  // changed
  {
    const { drive, row } = await restoredPinnedSettledDrive();
    const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    assert.equal(tabB.update(row.id, { pinned: false }).ok, true, 'tab B unpins the view');
    drive.api.renderSavedUI();
    assert.equal(drive.api.state.savedRefusal, 'changed');
    assert.equal(drive.api.state.financial.phase, 'ready', 'the stale results stay rendered');
    assert.equal(drive.api.exportQueryBody(), null, 'Export gets no body under the changed refusal');
  }
  // missing
  {
    const { drive, row } = await restoredPinnedSettledDrive();
    const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    sameJson(tabB.remove(row.id), { ok: true, deleted: true });
    drive.api.renderSavedUI();
    assert.equal(drive.api.state.savedRefusal, 'missing');
    assert.equal(drive.api.exportQueryBody(), null, 'Export gets no body under the missing refusal');
  }
  // store
  {
    const { drive } = await restoredPinnedSettledDrive();
    drive.storage.setItem(STORE_KEY, '{"contract":');
    drive.api.renderSavedUI();
    assert.equal(drive.api.state.savedRefusal, 'store');
    assert.equal(drive.api.exportQueryBody(), null, 'Export gets no body under the store refusal');
  }
  // The same edit is noticed even without a render first: the export seam
  // reconciles on its own, so a click can never re-POST unnoticed stale bytes.
  {
    const { drive, row } = await restoredPinnedSettledDrive();
    const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    assert.equal(tabB.update(row.id, { pinned: false }).ok, true, 'tab B unpins the view');
    assert.equal(drive.api.state.savedRefusal, '', 'the edit is not yet noticed');
    assert.equal(drive.api.exportQueryBody(), null, 'the export seam notices on its own');
    assert.equal(drive.api.state.savedRefusal, 'changed');
  }
});

test('T-R3-3-export-click: an export click under a saved-view refusal sends no workbook request', async () => {
  const xlsxCalls = (drive) => drive.fetchCalls.filter((call) => call.url.indexOf('/financial/query.xlsx') >= 0);
  // Control: with no refusal the same click does POST the ready body.
  {
    const { drive } = await restoredPinnedSettledDrive();
    assert.equal(drive.api.state.savedRefusal, '');
    drive.api.runExport();
    await new Promise((resolve) => setImmediate(resolve));
    const calls = xlsxCalls(drive);
    assert.equal(calls.length, 1, 'the control click posts once');
    assert.notEqual(calls[0].body, 'null', 'the control body is a real query body');
  }
  // changed / missing / store refusals: no workbook request at all.
  for (const make of [
    (drive, row) => freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' }).update(row.id, { pinned: false }),
    (drive, row) => freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' }).remove(row.id),
    (drive) => drive.storage.setItem(STORE_KEY, '{"contract":'),
  ]) {
    const { drive, row } = await restoredPinnedSettledDrive();
    make(drive, row);
    drive.api.runExport();
    await new Promise((resolve) => setImmediate(resolve));
    assert.notEqual(drive.api.state.savedRefusal, '', 'the click itself notices the refusal');
    assert.equal(xlsxCalls(drive).length, 0, 'no workbook request under the refusal');
  }
});

test('T-R3-3-race: a view unpinned in another tab mid-flight gets no stale digest backfill', async () => {
  const container = fixtureContainer('saved_pinned.json');
  const row = container.saved_views[0];
  const drive = harness();
  drive.storage.setItem(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  assert.equal(drive.api.restoreSavedView(row.id).ok, true, 'the pinned restore starts the fetch');
  // The fetch is in flight (its resolve rides microtasks): the "other tab"
  // unpins the view BEFORE the resolve handler runs.
  const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  assert.equal(tabB.update(row.id, { pinned: false }).ok, true, 'tab B unpins the view mid-flight');
  const afterEdit = drive.storage.getItem(STORE_KEY);
  await untilFinancialSettled(drive.api);
  assert.equal(drive.api.state.savedRefusal, 'changed', 'the resolve path refuses the unpinned view');
  assert.equal(drive.storage.getItem(STORE_KEY), afterEdit,
    'no stale saved_against digest landed in the edited view');
  const stored = JSON.parse(drive.storage.getItem(STORE_KEY)).saved_views[0];
  assert.equal(stored.saved_against.response_sha256, row.saved_against.response_sha256,
    'the stored digest is still the one the other tab left');
});

test('T-R3-3-control-pinned: with no edit in another tab a pinned resolve writes nothing', async () => {
  // MINOR-3 polarity (main's): a pinned view keeps the digest it was saved
  // with; the resolve path never rewrites it, even with a verified digest.
  const { drive } = restoredPinnedDrive();
  const beforeResolve = drive.storage.getItem(STORE_KEY);
  await untilFinancialSettled(drive.api);
  assert.equal(drive.api.state.financial.phase, 'ready', 'the pinned fetch settled');
  assert.equal(drive.api.state.savedRefusal, '', 'no refusal is active');
  assert.equal(drive.api.state.financial.responseSha256, RECORDED_SHA, 'the fetch verified its digest');
  assert.equal(drive.storage.getItem(STORE_KEY), beforeResolve, 'the pinned row bytes are unchanged');
});

test('T-R3-3-control-latest: with no edit in another tab a latest resolve backfills the verified digest', async () => {
  const container = fixtureContainer('saved_latest.json');
  const row = container.saved_views[0];
  assert.equal(row.saved_against.response_sha256, null, 'the latest fixture carries no digest yet');
  const drive = harness();
  drive.storage.setItem(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  assert.equal(drive.api.restoreSavedView(row.id).ok, true, 'the latest fixture view restores');
  drive.api.setTab('compare', false);
  await untilFinancialSettled(drive.api);
  assert.equal(drive.api.state.financial.phase, 'ready', 'the latest fetch settled');
  assert.equal(drive.api.state.savedRefusal, '', 'no refusal is active');
  assert.equal(drive.api.state.financial.responseSha256, RECORDED_SHA);
  const stored = JSON.parse(drive.storage.getItem(STORE_KEY)).saved_views[0];
  assert.equal(stored.saved_against.response_sha256, RECORDED_SHA,
    'the latest view records the verified digest of the answer it was served');
});

test('T-R3-3-race-request: a pinned request re-cut in another tab mid-flight refuses and gets no backfill', async () => {
  const container = fixtureContainer('saved_pinned.json');
  const row = container.saved_views[0];
  const drive = harness();
  drive.storage.setItem(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  assert.equal(drive.api.restoreSavedView(row.id).ok, true, 'the pinned restore starts the fetch');
  // Tab B keeps the view pinned but changes its request content while this
  // tab's fetch of the OLD bytes is in flight.
  const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  const edited = JSON.parse(JSON.stringify(row.request));
  edited.metric_ids = edited.metric_ids.slice(1);
  const updated = tabB.update(row.id, { request: edited });
  assert.equal(updated.ok, true, updated.reason || 'tab B re-cuts the pinned request');
  assert.equal(updated.view.pinned, true, 'the view stays pinned');
  const afterEdit = drive.storage.getItem(STORE_KEY);
  await untilFinancialSettled(drive.api);
  assert.equal(drive.api.state.savedRefusal, 'changed', 'the resolve path refuses the re-cut view');
  assert.equal(drive.api.activePinnedRequest(), null, 'no stale pinned bytes are served');
  assert.equal(drive.storage.getItem(STORE_KEY), afterEdit, 'the edited row bytes are unchanged');
});

// ── X2-b+c r3 R3-1 (repair): a pin flip re-runs the emitter's ref gate ──────

test('T-R3-1-unpin-dedup: an unpin that collapses two refs to one identity refuses and the row is unchanged', () => {
  const base = fixtureContainer('saved_pinned.json').saved_views[0];
  const { store } = r3Store();
  // Pinned, the two refs differ by version_ref (their accessions); latest
  // drops version_ref, so both project to one follow_head identity.
  const saved = store.save(Object.assign({}, base, {
    evidence_refs: [
      { accession: '0000320193-25-000073', occurrence_id: 'rawfact_shared', source_span: [1, 2] },
      { accession: '0000320193-24-000123', occurrence_id: 'rawfact_shared', source_span: [3, 4] }
    ]
  }));
  assert.equal(saved.ok, true, saved.reason || 'the pinned view with two versions saves');
  assert.equal(saved.view.pinned, true);
  const before = JSON.stringify(store.load(saved.view.id).view);
  const refused = store.update(saved.view.id, { pinned: false });
  sameJson(refused, { ok: false, reason: 'duplicate_reference', path: '$.evidence_refs[1]' });
  assert.equal(JSON.stringify(store.load(saved.view.id).view), before, 'the stored row is unchanged');
});

test('T-R3-1-pin-control: a pin that surfaces a control character as version_ref refuses and the row is unchanged', () => {
  const base = fixtureContainer('saved_latest.json').saved_views[0];
  const { store } = r3Store();
  // Latest, object_id is the occurrence and the accession is never projected.
  const saved = store.save(Object.assign({}, base, {
    evidence_refs: [{ accession: 'A' + CTRL, occurrence_id: 'rawfact_ok', source_span: [0, 1] }]
  }));
  assert.equal(saved.ok, true, saved.reason || 'the latest view saves');
  assert.equal(saved.view.pinned, false);
  const before = JSON.stringify(store.load(saved.view.id).view);
  const refused = store.update(saved.view.id, { pinned: true });
  sameJson(refused, { ok: false, reason: 'invalid_control', path: '$.evidence_refs[0].version_ref' });
  assert.equal(JSON.stringify(store.load(saved.view.id).view), before, 'the stored row is unchanged');
});

// ── X2-b+c r3 MINOR-4 (repair): the Export control agrees with the body ────

test('T-R3-MINOR4-button: a saved-view refusal disables Export and names the view as the cause', async () => {
  // Control: no refusal, the same health render leaves Export enabled.
  {
    const { drive } = await restoredPinnedSettledDrive();
    drive.api.applyHealth(drive.api.state.health);
    assert.equal(drive.api.state.savedRefusal, '');
    assert.equal(drive.api.ui.exportBtn.disabled, false, 'the control leaves Export enabled');
    assert.notEqual(drive.api.ui.exportBtn.getAttribute('data-tip-en'), 'Export unavailable for this view.');
  }
  {
    const { drive, row } = await restoredPinnedSettledDrive();
    const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    assert.equal(tabB.update(row.id, { pinned: false }).ok, true, 'tab B unpins the view');
    drive.api.applyHealth(drive.api.state.health);
    assert.equal(drive.api.state.savedRefusal, 'changed', 'the render notices the edit');
    assert.equal(drive.api.ui.exportBtn.disabled, true, 'Export is disabled under the refusal');
    assert.equal(drive.api.ui.exportBtn.getAttribute('data-tip-en'), 'Export unavailable for this view.');
    assert.equal(drive.api.ui.exportBtn.getAttribute('data-tip-zh'), '此视图暂不支持导出。');
    assert.equal(drive.api.ui.exportWrap.getAttribute('data-tip-en'), 'Export unavailable for this view.',
      'the wrapper carries the same tip for hover');
  }
});

// ── X2-b+c r4 MINOR-4: the refusal paths themselves refresh Export — no
// health render in between ────────────────────────────────────────────────

function assertExportRefused(drive, why) {
  assert.equal(drive.api.ui.exportBtn.disabled, true, why + ': Export is disabled');
  assert.equal(drive.api.ui.exportBtn.getAttribute('data-tip-en'), 'Export unavailable for this view.', why);
  assert.equal(drive.api.ui.exportBtn.getAttribute('data-tip-zh'), '此视图暂不支持导出。', why);
  assert.equal(drive.api.ui.exportWrap.getAttribute('data-tip-en'), 'Export unavailable for this view.',
    why + ': the wrapper carries the same tip for hover');
}

test('T-R4-MINOR4-render: another tab\'s edit noticed by renderSavedUI disables Export', async () => {
  const xlsxCalls = (drive) => drive.fetchCalls.filter((call) => call.url.indexOf('/financial/query.xlsx') >= 0);
  // changed: tab B unpins the view.
  {
    const { drive, row } = await restoredPinnedSettledDrive();
    assert.equal(drive.api.ui.exportBtn.disabled, false, 'Export starts enabled');
    const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    assert.equal(tabB.update(row.id, { pinned: false }).ok, true, 'tab B unpins the view');
    drive.api.renderSavedUI();
    assert.equal(drive.api.state.savedRefusal, 'changed');
    assertExportRefused(drive, 'changed via renderSavedUI');
    drive.api.runExport();
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(xlsxCalls(drive).length, 0, 'the disabled control sends no workbook request');
  }
  // missing: tab B deletes the view.
  {
    const { drive, row } = await restoredPinnedSettledDrive();
    const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    sameJson(tabB.remove(row.id), { ok: true, deleted: true });
    drive.api.renderSavedUI();
    assert.equal(drive.api.state.savedRefusal, 'missing');
    assertExportRefused(drive, 'missing via renderSavedUI');
  }
});

test('T-R4-MINOR4-restore: a refused restoreSavedView disables Export', async () => {
  const { drive, row } = await restoredPinnedSettledDrive();
  assert.equal(drive.api.ui.exportBtn.disabled, false, 'Export starts enabled');
  const tabB = freshBriefcase(drive.storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  sameJson(tabB.remove(row.id), { ok: true, deleted: true });
  const restored = drive.api.restoreSavedView(row.id);
  assert.equal(restored.ok, false);
  assert.equal(restored.reason, 'missing');
  assert.equal(drive.api.state.savedRefusal, 'missing');
  assertExportRefused(drive, 'missing via restoreSavedView');
});

// ── PF-3 re-resolve: a pinned view behind a newer generation re-resolves to
// latest, and the resolve that follows backfills the new answer's digest ────

test('T-R3-reresolve: re-resolving a stale pinned view stores latest cutoffs, the new generation and the served digest', async () => {
  const { drive, row } = await restoredPinnedSettledDrive();
  const newer = { id: 'ffprods_' + 'e5f6a7b8'.repeat(8), admitted_at: '2026-10-11T04:00:00Z' };
  drive.api.state.health.generation = newer;
  assert.ok(drive.api.savedGenerationStale(), 'the view is behind the newer generation');
  const result = drive.api.reResolveSavedView();
  assert.equal(result.ok, true, result.reason || 'the re-resolve updates the view');
  await untilFinancialSettled(drive.api);
  assert.equal(drive.api.state.financial.phase, 'ready', 'the re-resolved fetch settled');
  assert.equal(drive.api.state.savedRefusal, '', 'the re-resolved view is active, not refused');
  assert.equal(drive.api.state.pinnedRequest, null, 'no pinned bytes are served after the re-resolve');
  const stored = JSON.parse(drive.storage.getItem(STORE_KEY)).saved_views[0];
  assert.equal(stored.id, row.id);
  assert.equal(stored.pinned, false);
  assert.equal(stored.saved_against.generation_id, newer.id);
  assert.equal(stored.saved_against.admitted_at, newer.admitted_at);
  assert.equal(stored.saved_against.response_sha256, RECORDED_SHA,
    'the latest view records the digest of the answer the re-resolve served');
  assert.equal(drive.api.savedGenerationStale(), null, 'no stale chip after the re-resolve');
});

// ── X2-b+c r3 R3-4: the reconcile compare uses the store's own notion of
// equality (canonical bytes), never JSON.stringify's key order ────────────────

test('T-R3-4-canonical: a same-content reordered request is not refused; a content-different one still is', () => {
  // Same content, reordered keys (the Postgres jsonb order another writer
  // could leave behind): NOT a change.
  const container = fixtureContainer('saved_pinned.json');
  const row = container.saved_views[0];
  const drive = harness();
  drive.storage.setItem(STORE_KEY, JSON.stringify(container));
  drive.api.initSavedBriefcase();
  assert.equal(drive.api.restoreSavedView(row.id).ok, true, 'the pinned fixture view restores');
  const reordered = JSON.parse(drive.storage.getItem(STORE_KEY));
  const reverseKeys = (value) => {
    if (Array.isArray(value)) return value.map(reverseKeys);
    if (value && typeof value === 'object') {
      const out = {};
      Object.keys(value).reverse().forEach((key) => { out[key] = reverseKeys(value[key]); });
      return out;
    }
    return value;
  };
  reordered.saved_views[0] = reverseKeys(reordered.saved_views[0]);
  drive.storage.setItem(STORE_KEY, JSON.stringify(reordered));
  drive.api.renderSavedUI();
  assert.equal(drive.api.state.savedRefusal, '', 'a reordered request with the same content is not a change');
  const served = drive.api.activePinnedRequest();
  assert.ok(served, 'the pinned bytes are still served');

  // A request that differs in content still refuses.
  const edited = JSON.parse(drive.storage.getItem(STORE_KEY));
  edited.saved_views[0].request.metric_ids = edited.saved_views[0].request.metric_ids.slice();
  edited.saved_views[0].request.metric_ids[0] = 'revenue_changed';
  drive.storage.setItem(STORE_KEY, JSON.stringify(edited));
  drive.api.renderSavedUI();
  assert.equal(drive.api.state.savedRefusal, 'changed', 'a content-different request refuses');
  assert.equal(drive.api.activePinnedRequest(), null);
});

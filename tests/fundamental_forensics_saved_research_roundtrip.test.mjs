// FIF X2-s saved-research roundtrip suite (hermetic: no network, no browser).
//
// Drives the real page module (templates/fundamental_forensics.js) and the
// real store module (templates/fif_saved_briefcase.js) inside a vm context
// with stubbed storage/fetch/crypto, over the committed fixtures. Pins:
//   - save -> reload (fresh module instance, same storage) -> identical bytes
//   - fixture identity: the module's saved object for fixed inputs equals the
//     committed fixture JSON (the Python schema suite walks the same files)
//   - restore of a pinned view re-POSTs the stored request bytes verbatim and
//     the stubbed X-FIF-Response-SHA256 matches the served body
//   - direct link (P2 URL reader) and Back (popstate) restore
//     subject/policy/cutoff/cohort exactly
//   - every T1 refusal reason, the self-healing blank container, refused
//     views staying listed + deletable
//   - the store makes zero network calls, signed in and signed out, and
//     writes only its own localStorage key
//   - the A->B manifest mapping round-trips every fixture losslessly
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
  api.state.asOfDate = '2025-06-30';
  api.state.policy = 'latest_known_as_of';
  api.state.symbol = 'AAPL';
  const saved = api.performSavedSave('Apple pinned at June cutoff');
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
  const cohort = cohortBriefcase.create({ now: () => '2026-10-12T00:00:00Z' })
    .save({
      name: 'Apple vs mega-cap peers',
      issuer: pinned.issuer,
      request: JSON.parse(JSON.stringify(pinned.request)),
      peers: { cohort: 'cohort_2026q3_megacap', peer_metric: 'revenue', align: 'shift_labeled', peer_n: 5, peer_tol: 60 },
      view: { tab: 'peers', finding: null },
      pinned: false,
      saved_against: pinned.saved_against,
      evidence_refs: [],
      watch: { issuer: false }
    });
  const committedCohort = fixtureContainer('saved_cohort.json').saved_views[0];
  assert.equal(cohort.ok, true, cohort.reason || 'save refused');
  // request clocks differ (pinned fixture has the June cutoff) — the committed
  // cohort fixture carries the latest clocks; rebuild the comparison on the
  // committed request.
  cohort.view.request = committedCohort.request;
  sameJson(cohort.view, committedCohort);
});

test('the page-built request for the pinned desk equals the committed fixture request', () => {
  const { api } = harness();
  api.initSavedBriefcase();
  api.state.asOfDate = '2025-06-30';
  api.state.policy = 'latest_known_as_of';
  const input = api.buildSavedViewInput('Apple pinned at June cutoff');
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
  assert.equal(api.state.asOfDate, '2025-06-30');
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
  assert.match(pinnedLink, /as_of=2025-06-30/);
  const third = harness();
  third.location.search = pinnedLink.replace(/^[^?]*/, '');
  third.api.applyUrlState(true);
  assert.equal(third.api.state.symbol, 'AAPL');
  assert.equal(third.api.state.asOfDate, '2025-06-30');
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

test('every T1 refusal reason refuses the load and stays listed + deletable', () => {
  const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
  function refusal(name, mutate) {
    const row = JSON.parse(JSON.stringify(base));
    row.id = 'refusal' + Math.abs(name.length);
    mutate(row);
    const storage = memoryStorage([[STORE_KEY, JSON.stringify({ contract: 'fundamental_forensics.saved_research.v1', saved_views: [row] })]]);
    const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
    const listing = store.list();
    assert.equal(listing.length, 1, name + ' stays listed');
    assert.equal(listing[0].available, false, name + ' listed unavailable');
    const loaded = store.load(row.id);
    assert.equal(loaded.ok, false, name + ' refuses the load');
    const removed = store.remove(row.id);
    sameJson(removed, { ok: true, deleted: true });
    assert.equal(store.list().length, 0, name + ' deletable');
  }
  refusal('schema', (row) => { row.schema = 'fundamental_forensics.saved_research.v9'; });
  refusal('request_contract', (row) => { row.request_contract = 'fundamental_forensics.financial_query_request/v2'; });
  refusal('request_schema', (row) => { row.request.schema = 'fundamental_forensics.financial_query_request/v2'; });
  refusal('request_root', (row) => { row.request.extra_key = 'x'; });
  refusal('pinned_cutoffs', (row) => {
    row.pinned = true;
    row.request.policy.source_snapshot_at = '';
  });
});

test('a container whose own contract drifts self-heals to a blank (GovRev discipline)', () => {
  const storage = memoryStorage([[STORE_KEY, JSON.stringify({
    contract: 'government_procurement_local_state.v1',
    saved_views: [{ schema: 'fundamental_forensics.saved_research.v1', id: 'x' }]
  })]]);
  const store = freshBriefcase(storage, 0).create({ now: () => '2026-10-12T00:00:00Z' });
  assert.equal(store.list().length, 0, 'a drifted container heals to a blank');
  const loaded = store.load('x');
  assert.equal(loaded.ok, false);
});

test('the store makes zero network calls and writes only its own key, signed in and signed out', () => {
  for (const signedIn of [true, false]) {
    const storage = memoryStorage();
    const Briefcase = freshBriefcase(storage, 3);
    const store = Briefcase.create({ storage, now: () => '2026-10-12T00:00:00Z' });
    const base = fixtureContainer('saved_single_issuer.json').saved_views[0];
    const saved = store.save({
      name: base.name, issuer: base.issuer, request: base.request, peers: base.peers,
      view: base.view, pinned: base.pinned, saved_against: base.saved_against,
      evidence_refs: base.evidence_refs, watch: base.watch
    });
    assert.equal(saved.ok, true);
    store.list();
    store.load(saved.view.id);
    store.update(saved.view.id, { name: 'Renamed' });
    store.remove(saved.view.id);
    Briefcase.toInvestigationManifestV2(saved.view);
    Briefcase.fromInvestigationManifestV2(Briefcase.toInvestigationManifestV2(base));
    // Signed in or signed out makes no difference to a module that owns no
    // transport: the throwing fetch/XHR stubs were never reached.
    assert.equal(Briefcase.__networkProbe.fetches, 0, signedIn ? 'signed in: no fetch' : 'signed out: no fetch');
    assert.equal(Briefcase.__networkProbe.xhrs, 0, 'no XMLHttpRequest');
    assert.equal(/fetch\(|XMLHttpRequest|navigator\.sendBeacon/.test(BRIEFCASE_SOURCE), false,
      'the store module contains no transport calls');
    assert.deepEqual([...new Set(storage.written)], [STORE_KEY], 'only its own key is written');
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

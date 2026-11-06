// Execute the exact native IIFE and research candidate under deterministic
// DOM/fetch/timer adapters. This is not an actual browser or deployed test.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const sha = s => crypto.createHash('sha256').update(s).digest('hex');
const native = fs.readFileSync(path.join(HERE, 'pinned_cn_prophet_live.js'), 'utf8');
const candidate = fs.readFileSync(path.join(HERE, 'candidate_cn_prophet_live.js'), 'utf8');
assert.equal(sha(native), 'e4bfdad0781eda00f8c940047e637a6f4ac691b057b703f9eba25d9930665147');
const MAXAGE = 900000;
const BASE = Date.parse('2026-10-09T02:00:00Z');

function element() {
  const el = { hidden: true, className: 'pv-live', children: [], attrs: {}, ownText: '',
    appendChild(child) { this.children.push(child); },
    setAttribute(k, v) { this.attrs[k] = v; },
    removeAttribute(k) { delete this.attrs[k]; },
    getAttribute(k) { return this.attrs[k] ?? null; },
  };
  Object.defineProperties(el, {
    textContent: { get() { return this.ownText + this.children.map(x => x.textContent).join(''); }, set(v) { this.ownText = v; this.children = []; } },
    innerHTML: { get() { return this.textContent; }, set(v) { assert.equal(v, ''); this.ownText = ''; this.children = []; } },
  });
  return el;
}

function harness(source, { missingHeader = false, initiallyHidden = false } = {}) {
  let now = BASE, nextTimer = 1;
  const timers = new Map(), listeners = {}, requests = [];
  const cards = ['000001.SZ', '000002.SZ'].map(ticker => ({ ticker, ssrText: 'unchanged-' + ticker, getAttribute(k) { return k === 'data-ticker' ? ticker : null; } }));
  const slots = cards.map(card => { const el = element(); el.closest = () => card; return el; });
  const doc = {
    visibilityState: initiallyHidden ? 'hidden' : 'visible', readyState: 'complete',
    getElementById(id) { return !missingHeader && id === 'stocks-header' ? { getAttribute: () => '2026-10-09' } : null; },
    querySelectorAll(selector) { assert.equal(selector, '.pvcard[data-ticker] .pv-live'); return slots; },
    createElement(tag) { assert.equal(tag, 'span'); return element(); },
    addEventListener(name, fn) { (listeners[name] ??= []).push(fn); },
  };
  function schedule(fn, wait, interval = 0) {
    const id = nextTimer++;
    assert.ok(Number.isFinite(wait) && wait >= 0);
    timers.set(id, { fn, at: now + wait, interval });
    return id;
  }
  class Clock extends Date { static now() { return now; } }
  const context = {
    document: doc, Date: Clock,
    setTimeout: (fn, delay) => schedule(fn, delay), clearTimeout: id => timers.delete(id),
    setInterval: (fn, delay) => schedule(fn, delay, delay), clearInterval: id => timers.delete(id),
    // The fake records abort but permits manual late resolution, challenging
    // sequence guards even when a transport ignores cancellation.
    AbortController: class { constructor() { this.signal = { aborted: false }; } abort() { this.signal.aborted = true; } },
    fetch(url, options) { return new Promise((resolve, reject) => requests.push({ url, options, resolve, reject, answered: false })); },
  };
  vm.runInNewContext(source, context, { filename: 'cn_prophet_live.js', timeout: 1000 });
  const flush = async () => { for (let i = 0; i < 15; i++) await Promise.resolve(); };
  function payload(change = {}) {
    return { schema: 'cn_prophet_live.states/v1', session: '2026-10-09', built_at: new Date(now).toISOString(), status: 'ok',
      names: { '000001.SZ': { state: 'forming', market_status: 'trading' } }, ...change };
  }
  async function respond(index, status, body = payload(), malformed = false) {
    const req = requests[index]; assert.ok(req && !req.answered); req.answered = true;
    req.resolve({ status, ok: status >= 200 && status < 300,
      json: () => malformed ? Promise.reject(new SyntaxError('synthetic invalid JSON')) : Promise.resolve(body) });
    await flush();
  }
  async function networkError(index) { const req = requests[index]; req.answered = true; req.reject(new Error('synthetic network error')); await flush(); }
  async function advance(ms) {
    const target = now + ms;
    for (let n = 0; n < 10000; n++) {
      const due = [...timers.entries()].filter(([, t]) => t.at <= target).sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
      if (!due) { now = target; await flush(); return; }
      const [id, timer] = due; now = timer.at;
      if (timer.interval) timer.at += timer.interval; else timers.delete(id);
      timer.fn(); await flush();
    }
    throw new Error('timer loop');
  }
  async function visibility(value) { doc.visibilityState = value; for (const fn of listeners.visibilitychange ?? []) fn(); await flush(); }
  async function jumpSuspended(ms) { now += ms; await flush(); }
  function snapshot() { return { visible: !slots[0].hidden, text: slots[0].textContent, attrs: { ...slots[0].attrs }, cards: cards.map(x => [x.ticker, x.ssrText]), requests: requests.length }; }
  return { respond, networkError, advance, visibility, jumpSuspended, requests, payload, snapshot, slots, get now() { return now; } };
}

const tests = [];
function record(name, original, repaired, expectation, details = {}) {
  assert.equal(repaired, expectation, name);
  tests.push({ name, status: 'PASS', native_observed: original, candidate_observed: repaired, required_candidate: expectation, ...details });
}

for (const status of [500, 503, 404, 429]) {
  const values = [];
  for (const code of [native, candidate]) {
    const h = harness(code); await h.respond(0, 200); await h.advance(120000); await h.respond(1, status);
    values.push(h.snapshot().visible);
  }
  assert.equal(values[0], true);
  record('non-OK ' + status + ' removes prior live chip', ...values, false);
}

for (const mode of ['401', '403', 'network', 'invalid_json', '204_empty', 'bad_schema', 'old_session', 'stale', 'dark', 'invalid_clock']) {
  const values = [];
  for (const code of [native, candidate]) {
    const h = harness(code); await h.respond(0, 200); await h.advance(120000);
    if (mode === 'network') await h.networkError(1);
    else if (mode === 'invalid_json' || mode === '204_empty') await h.respond(1, mode === '204_empty' ? 204 : 200, {}, true);
    else if (mode === '401' || mode === '403') await h.respond(1, Number(mode));
    else {
      const changes = {
        bad_schema: { schema: 'unexpected' }, old_session: { session: '2026-10-08' },
        stale: { built_at: new Date(h.now - MAXAGE - 1).toISOString() }, dark: { status: 'dark' }, invalid_clock: { built_at: 'not-a-time' },
      };
      await h.respond(1, 200, h.payload(changes[mode]));
    }
    values.push(h.snapshot().visible);
  }
  assert.equal(values[0], false);
  record('existing refusal preserved: ' + mode, ...values, false);
}

for (const age of [MAXAGE, MAXAGE - 1]) {
  const values = [];
  for (const code of [native, candidate]) { const h = harness(code); await h.respond(0, 200, h.payload({ built_at: new Date(h.now - age).toISOString() })); values.push(h.snapshot().visible); }
  record('absolute expiry admission boundary age=' + age, ...values, age < MAXAGE);
}

for (const future of [86400000, 30000]) {
  const values = [];
  for (const code of [native, candidate]) { const h = harness(code); await h.respond(0, 200, h.payload({ built_at: new Date(h.now + future).toISOString() })); values.push(h.snapshot().visible); }
  assert.equal(values[0], true);
  record('future artifact offset=' + future, ...values, future <= 60000, { explicit_research_skew_allowance_ms: 60000 });
}

{
  const values = [];
  for (const code of [native, candidate]) {
    const h = harness(code); await h.respond(0, 200, h.payload({ built_at: new Date(h.now - MAXAGE + 10000).toISOString() }));
    await h.advance(10000); values.push(h.snapshot().visible);
  }
  assert.equal(values[0], true);
  record('last-good artifact expires at its own deadline between polls', ...values, false);
}

{
  const values = [], requestCounts = [];
  for (const code of [native, candidate]) {
    const h = harness(code); await h.respond(0, 200); await h.advance(MAXAGE + 1);
    values.push(h.snapshot().visible); requestCounts.push(h.requests.length);
  }
  assert.equal(values[0], true);
  assert.ok(requestCounts[1] > requestCounts[0]);
  record('hanging response cannot keep last chip past expiry and polling can retry', ...values, false, { native_requests: requestCounts[0], candidate_requests: requestCounts[1] });
}

{
  const values = [];
  for (const code of [native, candidate]) {
    const h = harness(code); await h.respond(0, 200); await h.visibility('hidden'); await h.jumpSuspended(MAXAGE + 1);
    await h.visibility('visible'); values.push(h.snapshot().visible);
  }
  assert.equal(values[0], true);
  record('visibility resumption expires last chip before a fresh response', ...values, false);
}

for (const latest of ['auth_refusal', 'newer_state']) {
  const values = [];
  for (const code of [native, candidate]) {
    const h = harness(code); await h.respond(0, 200); await h.visibility('visible'); await h.visibility('visible');
    if (latest === 'auth_refusal') await h.respond(2, 401);
    else await h.respond(2, 200, h.payload({ names: { '000001.SZ': { state: 'near', market_status: 'trading' } } }));
    await h.respond(1, 200, h.payload());
    const state = h.snapshot(); values.push(latest === 'auth_refusal' ? state.visible : state.text.includes('Forming'));
  }
  assert.equal(values[0], true);
  record('obsolete forced response cannot override ' + latest, ...values, false);
}

{
  const h = harness(candidate); await h.respond(0, 200); const before = h.snapshot().cards;
  await h.advance(120000); await h.respond(1, 500); const after = h.snapshot();
  assert.deepEqual(after.cards, before); assert.deepEqual(after.attrs, {});
  record('teardown preserves exact SSR card order/content and clears live tooltip', null, true, true);
}

{
  const h = harness(candidate); await h.respond(0, 200); await h.advance(120000); await h.respond(1, 500);
  await h.advance(120000); await h.respond(2, 200);
  assert.ok(h.snapshot().text.includes('Forming') && h.snapshot().text.includes('正在形成'));
  record('a later valid response restores the unchanged observational vocabulary', null, h.snapshot().visible, true);
}

{
  const h = harness(candidate, { missingHeader: true }); assert.equal(h.requests.length, 0);
  record('page without existing stocks header does not create a live runtime', null, h.snapshot().visible, false);
}

{
  const values = [], aborted = [];
  for (const code of [native, candidate]) {
    const h = harness(code); await h.visibility('visible'); await h.advance(30000);
    aborted.push(h.requests.every(r => r.options.signal?.aborted === true));
    await h.respond(0, 200); await h.respond(1, 200);
    values.push(h.snapshot().visible);
  }
  assert.deepEqual(aborted, [false, true]);
  record('all hanging requests abort at deadline and late results stay obsolete', ...values, false, { native_all_aborted: aborted[0], candidate_all_aborted: aborted[1] });
}

assert.equal(candidate.match(/var POLL = (\d+)/)[1], native.match(/var POLL = (\d+)/)[1]);
assert.equal(candidate.match(/var MAXAGE = (\d+)/)[1], native.match(/var MAXAGE = (\d+)/)[1]);
assert.equal(candidate.slice(candidate.indexOf('  var STATE ='), candidate.indexOf('  var _bakedSession;')),
             native.slice(native.indexOf('  var STATE ='), native.indexOf('  var _bakedSession;')));
record('poll cadence, maximum age and STATE/STATUS vocabulary are unchanged', true, true, true);

const result = {
  status: 'PASS', source_pin: '3d90aad6d83152dfeeaf8345bc995826ac9d3139',
  native_template_and_site_git_blob: '5a4d08eab3ee4eebb587d19cbbd085322fb47a73',
  native_sha256: sha(native), candidate_sha256: sha(candidate), harness_sha256: sha(fs.readFileSync(fileURLToPath(import.meta.url))),
  node_version: process.version, test_count: tests.length, tests,
  explicit_research_choices: { request_deadline_ms: 30000, future_artifact_clock_allowance_ms: 60000, expiry_inclusive: true },
  limits: ['The exact IIFE runs in Node with a small DOM/fetch/timer adapter; this is not browser, layout, authenticated-service or deployed-source proof.',
    'All payloads, statuses, clocks and network failures are synthetic. No network or operational writes occur.',
    'Browser/device clock accuracy, hidden/frozen-tab scheduling, actual installed script bytes and natural API receipts remain implementation acceptance gates.',
    'The candidate is a research copy. Both actual paired production files must be updated through their existing owner if implementation is authorized.'],
};
fs.writeFileSync(path.join(HERE, 'results.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify({ status: result.status, tests: tests.length, native_failure_cases: tests.filter(t => t.native_observed !== null && t.native_observed !== t.required_candidate).length, candidate_sha256: result.candidate_sha256 }));

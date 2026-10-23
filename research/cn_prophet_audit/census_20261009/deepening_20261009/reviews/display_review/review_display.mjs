import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SUBJECT = path.resolve(HERE, '../../display_lab');
const hash = raw => crypto.createHash('sha256').update(raw).digest('hex');
const manifestRaw = fs.readFileSync(path.join(SUBJECT, 'MANIFEST.json'));
const MANIFEST = '5bb6c5b3b76d1f2739bd5f362b042c11b3d4e17d5f57fa4552c38ad83864b549';
assert.equal(hash(manifestRaw), MANIFEST);
const manifest = JSON.parse(manifestRaw);
for (const [name, identity] of Object.entries(manifest.files)) {
  const raw = fs.readFileSync(path.join(SUBJECT, name));
  assert.equal(hash(raw), identity.sha256, name);
  assert.equal(raw.length, identity.bytes, name);
}
const candidate = fs.readFileSync(path.join(SUBJECT, 'candidate_cn_prophet_live.js'), 'utf8');
const native = fs.readFileSync(path.join(SUBJECT, 'pinned_cn_prophet_live.js'), 'utf8');
assert.equal(hash(candidate), '595b83e907eabfb9e0df4ba3df4a2c3aad0f606c993ac345e4fccfd47d2176bc');
const BASE = Date.parse('2026-10-09T02:00:00.000Z');
const AGE = 900000;
const flush = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };

function deferred() {
  let resolve, reject;
  const promise = new Promise((a, b) => { resolve = a; reject = b; });
  return { promise, resolve, reject };
}

function node() {
  const el = { hidden: true, className: 'pv-live', children: [], own: '', attrs: {},
    appendChild(value) { this.children.push(value); },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    removeAttribute(k) { delete this.attrs[k]; },
    getAttribute(k) { return this.attrs[k] ?? null; } };
  Object.defineProperties(el, {
    textContent: { get() { return this.own + this.children.map(c => c.textContent).join(''); },
                   set(v) { this.own = String(v); this.children = []; } },
    innerHTML: { get() { return this.textContent; },
                 set(v) { assert.equal(v, ''); this.own = ''; this.children = []; } },
  });
  return el;
}

function runtime(code, { abortSupport = true, noHeader = false } = {}) {
  let now = BASE, nextId = 1;
  const pending = new Map(), requests = [], events = new Map(), selectors = [];
  const cards = ['000001.SZ', '000002.SZ'].map((ticker, i) => Object.freeze({
    ticker, rank: i + 1, ssr: 'Original score and text ' + ticker,
    getAttribute(key) { assert.equal(key, 'data-ticker'); return ticker; },
  }));
  const slots = cards.map(card => { const n = node(); n.closest = key => { assert.equal(key, '.pvcard'); return card; }; return n; });
  const document = { readyState: 'complete', visibilityState: 'visible',
    getElementById(id) { return id === 'stocks-header' && !noHeader ? { getAttribute: () => '2026-10-09' } : null; },
    querySelectorAll(selector) { selectors.push(selector); assert.equal(selector, '.pvcard[data-ticker] .pv-live'); return slots; },
    createElement(tag) { assert.equal(tag, 'span'); return node(); },
    addEventListener(name, fn) { if (!events.has(name)) events.set(name, []); events.get(name).push(fn); },
  };
  function timer(fn, delay, period = 0) {
    assert.ok(Number.isFinite(delay) && delay >= 0);
    const id = nextId++; pending.set(id, { fn, due: now + delay, period }); return id;
  }
  class Clock extends Date { static now() { return now; } }
  const context = { document, Date: Clock,
    setTimeout: (fn, d) => timer(fn, d), clearTimeout: id => pending.delete(id),
    setInterval: (fn, d) => timer(fn, d, d), clearInterval: id => pending.delete(id),
    fetch(url, options) {
      const headers = deferred(), body = deferred();
      const request = { started: now, url, options, headers, body, headerDone: false, bodyDone: false };
      requests.push(request);
      return headers.promise;
    },
  };
  if (abortSupport) context.AbortController = class {
    constructor() { this.signal = { aborted: false }; }
    abort() { this.signal.aborted = true; }
  };
  vm.runInNewContext(code, context, { timeout: 1000 });
  function data(change = {}) {
    return { schema: 'cn_prophet_live.states/v1', session: '2026-10-09', status: 'ok',
      built_at: new Date(now).toISOString(), names: { '000001.SZ': { state: 'forming', market_status: 'trading' } }, ...change };
  }
  async function headers(index, status = 200) {
    const r = requests[index]; assert.ok(r && !r.headerDone); r.headerDone = true;
    r.headers.resolve({ status, ok: status >= 200 && status < 300, json: () => r.body.promise });
    await flush();
  }
  async function body(index, value = data()) {
    const r = requests[index]; assert.ok(r && !r.bodyDone); r.bodyDone = true; r.body.resolve(value); await flush();
  }
  async function respond(index, status = 200, value = data()) {
    await headers(index, status); if (status >= 200 && status < 300) await body(index, value); else await flush();
  }
  async function reject(index, where = 'headers') {
    requests[index][where].reject(new Error('Independent synthetic ' + where + ' failure')); await flush();
  }
  async function run(ms) {
    const target = now + ms;
    for (let iteration = 0; iteration < 10000; iteration++) {
      const due = [...pending.entries()].filter(([, t]) => t.due <= target)
        .sort((a, b) => a[1].due - b[1].due || a[0] - b[0])[0];
      if (!due) { now = target; await flush(); return; }
      const [id, t] = due; now = Math.max(now, t.due);
      if (t.period) t.due += t.period; else pending.delete(id);
      t.fn(); await flush();
    }
    throw new Error('unbounded timer iteration');
  }
  async function visibility(value = 'visible') {
    document.visibilityState = value; for (const fn of events.get('visibilitychange') ?? []) fn(); await flush();
  }
  function snapshot() {
    return { now: new Date(now).toISOString(), visible: !slots[0].hidden,
      text: slots[0].textContent, tooltips: { ...slots[0].attrs },
      cards: cards.map(c => ({ ticker: c.ticker, rank: c.rank, ssr: c.ssr })),
      requests: requests.length, request_times: requests.map(r => new Date(r.started).toISOString()),
      request_aborts: requests.map(r => r.options.signal?.aborted ?? null) };
  }
  return { data, headers, body, respond, reject, run, visibility, snapshot, requests,
    jump(ms) { now += ms; }, get now() { return now; }, slots };
}

const checks = [];
function record(name, value, expected, detail = {}) {
  checks.push({ name, status: value === expected ? 'PASS' : 'FAIL', observed: value, expected, ...detail });
}

// The callback can be delayed while an asynchronous fetch/body completion is
// consumed first. Fresh artifact age must not be mistaken for request age.
for (const stage of ['headers', 'body']) {
  const observed = [];
  for (const code of [native, candidate]) {
    const h = runtime(code);
    if (stage === 'body') await h.headers(0);
    h.jump(30001); // no timer callback has executed in this permitted ordering
    if (stage === 'headers') await h.respond(0); else await h.body(0);
    const beforeTimers = h.snapshot();
    await h.run(0);
    observed.push({ before_queued_timers: beforeTimers, after_queued_timers: h.snapshot() });
  }
  record('absolute request deadline survives delayed timer: ' + stage,
    observed[1].after_queued_timers.visible, false,
    { family: 'D1', native: observed[0], candidate: observed[1],
      synthetic_order: 'request at 02:00:00; wall clock +30001ms without timer callbacks; fresh response consumed; queued timers then run' });
}

for (const kind of ['header_error', 'body_error', 'old_body_after_new_auth', 'old_body_after_new_state']) {
  const h = runtime(candidate); await h.respond(0); await h.visibility();
  if (kind.startsWith('old_body') || kind === 'body_error') await h.headers(1);
  await h.visibility();
  if (kind === 'old_body_after_new_auth') await h.respond(2, 401);
  else await h.respond(2, 200, h.data({ names: { '000001.SZ': { state: 'near', market_status: 'trading' } } }));
  if (kind === 'header_error') await h.reject(1);
  else if (kind === 'body_error') await h.reject(1, 'body');
  else await h.body(1);
  record('obsolete completion cannot change latest result: ' + kind,
    kind === 'old_body_after_new_auth' ? h.snapshot().visible : h.snapshot().text.includes('Near临近'),
    kind !== 'old_body_after_new_auth', { candidate: h.snapshot() });
}

{
  const h = runtime(candidate); await h.respond(0); await h.visibility(); await h.run(10000); await h.visibility();
  await h.respond(2, 200, h.data({ names: { '000001.SZ': { state: 'near', market_status: 'session_break' } } }));
  await h.run(20000);
  record('obsolete deadline cannot erase newer chip', h.snapshot().text.includes('Near · Lunch break临近 · 盘中暂歇'), true,
    { candidate: h.snapshot() });
}

{
  const h = runtime(candidate, { abortSupport: false }); await h.run(30000); await h.respond(0);
  record('timeout sequence guard works without AbortController', h.snapshot().visible, false);
  await h.run(90000); await h.respond(1);
  record('poll recovers without AbortController', h.snapshot().visible, true);
}

{
  const h = runtime(candidate); await h.respond(0); await h.visibility(); await h.headers(1); await h.run(30000); await h.body(1);
  record('body completed after executed timeout remains obsolete', h.snapshot().visible, false);
  await h.run(90000); await h.respond(2);
  record('poll recovers after executed body timeout', h.snapshot().visible, true);
}

for (const [name, age, expected] of [['last admissible millisecond', AGE - 1, true],
  ['inclusive age refusal', AGE, false], ['exact future tolerance', -60000, true],
  ['beyond future tolerance', -60001, false]]) {
  const h = runtime(candidate); await h.respond(0, 200, h.data({ built_at: new Date(h.now - age).toISOString() }));
  record(name, h.snapshot().visible, expected);
}

{
  const h = runtime(candidate); await h.respond(0, 200, h.data({ built_at: new Date(h.now - AGE + 1).toISOString() }));
  await h.run(1); record('accepted near-expiry artifact tears down at exact boundary', h.snapshot().visible, false);
}

{
  const h = runtime(candidate); await h.respond(0); await h.visibility('hidden'); h.jump(AGE + 1); await h.visibility('visible');
  record('suspended expiry checked before new forced response', h.snapshot().visible, false);
}

for (const status of [404, 429, 500, 503]) {
  const h = runtime(candidate); await h.respond(0); const before = h.snapshot().cards;
  await h.run(120000); await h.respond(1, status);
  record('non-OK ' + status + ' tears down live layer', h.snapshot().visible, false);
  record('non-OK ' + status + ' preserves exact SSR and removes tooltips',
    JSON.stringify(before) === JSON.stringify(h.snapshot().cards) && Object.keys(h.snapshot().tooltips).length === 0, true);
}

{
  const h = runtime(candidate); await h.respond(0); await h.run(120000); await h.headers(1); await h.reject(1, 'body');
  record('current malformed body clears old chip', h.snapshot().visible, false);
  await h.run(120000); await h.respond(2);
  record('recovery keeps both vocabulary spans', h.snapshot().text === 'Forming正在形成', true);
}

{
  const h = runtime(candidate, { noHeader: true });
  record('header gate preserves SSR-only page', h.requests.length === 0 && !h.snapshot().visible, true);
}

const block = code => code.slice(code.indexOf('  var STATE ='), code.indexOf('  var _bakedSession;'));
record('complete bilingual STATE/STATUS source block unchanged', block(candidate) === block(native), true);

// This preexisting enum fallback is not counted as a new deadline-repair defect.
const advisory = [];
for (const code of [native, candidate]) {
  const h = runtime(code); await h.respond(0, 200, h.data({ names: { '000001.SZ': { state: 'confirmed', market_status: 'trading' } } }));
  advisory.push(h.snapshot());
}

for (const [name, identity] of Object.entries(manifest.files)) {
  assert.equal(hash(fs.readFileSync(path.join(SUBJECT, name))), identity.sha256, 'subject changed: ' + name);
}
assert.equal(hash(fs.readFileSync(path.join(SUBJECT, 'MANIFEST.json'))), MANIFEST);
const result = { schema: 'cn-display-independent-review/v1',
  status: checks.some(c => c.status === 'FAIL') ? 'BLOCKED' : 'ACCEPTED_RESEARCH_SCOPE',
  subject_manifest_sha256: MANIFEST, candidate_sha256: hash(candidate), native_sha256: hash(native),
  review_code_sha256: hash(fs.readFileSync(fileURLToPath(import.meta.url))), node_version: process.version,
  counts: { checks: checks.length, pass: checks.filter(c => c.status === 'PASS').length,
            fail: checks.filter(c => c.status === 'FAIL').length }, checks,
  preexisting_scope_note: { name: 'unknown wire enum is echoed by both versions', native: advisory[0], candidate: advisory[1],
    interpretation: 'The unchanged source vocabulary table does not itself validate arbitrary wire enums. This is preexisting and not counted as a new expiry/concurrency repair blocker.' },
  limits: ['Deterministic Node evidence; no claim about measured browser task scheduling, layout, deployment or device-clock accuracy.',
           'All network payloads and clock/failure schedules are synthetic. No browser/network/operational writes.'],
};
fs.writeFileSync(path.join(HERE, 'REVIEW_RESULTS.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({ status: result.status, counts: result.counts, candidate_sha256: result.candidate_sha256,
  results_sha256: hash(fs.readFileSync(path.join(HERE, 'REVIEW_RESULTS.json'))) }));

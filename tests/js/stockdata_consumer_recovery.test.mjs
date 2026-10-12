/**
 * templates/stockdata.js consumer recovery (S3-01 consumer half, docket #8757).
 *
 * loadIndexes() is fail-OPEN: a market whose index read failed comes back as an empty
 * part. The loader re-fetches once its failure window closes, but only when somebody
 * asks again — and the Watchlist / Portfolio pages asked once, at init. This suite
 * pins the two read-only additions consumers use to ask again without polling:
 *
 *   indexRetryAt(markets)            earliest failure window among unloaded markets
 *   indexRecovery(marketsFn, cb)     { check } — one timer per failed market for when
 *                                    its window closes, plus re-asks on
 *                                    `visibilitychange` (visible) and `online`
 *
 * Every test runs the REAL module in a `vm` context with a fake fetch, a fake clock and
 * a fake setTimeout queue, so "after the failure TTL" is a clock advance, not a sleep.
 * Set STOCKDATA_JS to run the suite against another build (main has no indexRecovery,
 * so every test here reds there).
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const MODULE_PATH = process.env.STOCKDATA_JS || join(ROOT, 'templates', 'stockdata.js');
const SOURCE = readFileSync(MODULE_PATH, 'utf8');

const US_INDEX = 'stockdata/index.json';
const HK_INDEX = 'hkstockdata/index.json';
const count = (calls, url) => calls.filter((u) => u === url).length;
const plain = (x) => JSON.parse(JSON.stringify(x));

const TTL_NET = 30 * 1000;   // stockdata.js NEG_TTL_NET
const SLACK = 250;           // stockdata.js RECOVER_SLACK

const US_ROWS = [{ t: 'AAA', n: 'Alpha' }, { t: 'BBB', n: 'Beta' }];
const HK_ROWS = [{ t: '0700', n: 'Tencent' }];

function deferred() {
  let resolve, reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

function makeResponse(status, body, headers) {
  const h = {};
  Object.keys(headers || {}).forEach((k) => { h[k.toLowerCase()] = headers[k]; });
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (k) => (h[k.toLowerCase()] ?? null) },
    json: () => Promise.resolve(body),
  };
}
const respond = (status, body, headers) => Promise.resolve(makeResponse(status, body, headers));

// Settle every pending promise chain (the module's and the fake fetch's).
async function flush() { for (let i = 0; i < 12; i++) await new Promise((r) => setImmediate(r)); }

function makeBus() {
  const ls = {};
  return {
    add(type, fn) { (ls[type] = ls[type] || []).push(fn); },
    fire(type) { (ls[type] || []).slice().forEach((fn) => fn({ type })); },
    count(type) { return (ls[type] || []).length; },
  };
}

// One fresh module per test: fake fetch, fake clock, fake timer queue, real event buses.
function makeCtx(route) {
  const clock = { t: 1700000000000 };
  const calls = [];
  const timers = { seq: 0, q: [] };
  const docBus = makeBus();
  const winBus = makeBus();
  const doc = {
    hidden: false,
    documentElement: { getAttribute: () => 'en' },
    addEventListener: (t, fn) => docBus.add(t, fn),
  };
  const nav = { onLine: true };
  const sandbox = {
    window: { addEventListener: (t, fn) => winBus.add(t, fn) },
    document: doc,
    navigator: nav,
    console,
    fetch: (url) => { calls.push(String(url)); return route(String(url)); },
    setTimeout: (fn, ms) => {
      const id = ++timers.seq;
      timers.q.push({ id, at: clock.t + Math.max(0, ms || 0), fn });
      return id;
    },
    clearTimeout: (id) => { timers.q = timers.q.filter((x) => x.id !== id); },
    __clock: clock,
  };
  const ctx = vm.createContext(sandbox);
  vm.runInContext('Date.now = function () { return __clock.t; };', ctx);
  vm.runInContext(SOURCE, ctx);

  // Move the clock forward, running every timer that comes due (in deadline order) and
  // settling the promise chains each one starts.
  async function advance(ms) {
    const end = clock.t + ms;
    for (;;) {
      timers.q.sort((a, b) => a.at - b.at);
      const next = timers.q[0];
      if (!next || next.at > end) break;
      timers.q.shift();
      clock.t = Math.max(clock.t, next.at);
      next.fn();
      await flush();
    }
    clock.t = end;
    await flush();
  }
  return { SD: sandbox.window.SD, clock, calls, timers, doc, nav, docBus, winBus, advance };
}

// Index route: the US index answers from `plan` in order, the last entry repeating.
function usPlan(plan) {
  let i = 0;
  return (url) => {
    if (url === US_INDEX) {
      const step = plan[Math.min(i, plan.length - 1)];
      i += 1;
      return typeof step === 'function' ? step() : respond(step.status, step.body, step.headers);
    }
    return respond(404, {});
  };
}
const FAIL_503 = { status: 503, body: {} };
const OK_US = { status: 200, body: US_ROWS };

test('API: indexRetryAt / indexRecovery are exported', () => {
  const { SD } = makeCtx(usPlan([OK_US]));
  assert.equal(typeof SD.indexRetryAt, 'function', 'SD.indexRetryAt must exist');
  assert.equal(typeof SD.indexRecovery, 'function', 'SD.indexRecovery must exist');
});

test('one 503 at init: the consumer re-asks once the failure TTL elapses and the index fills', async () => {
  const { SD, calls, clock, timers, advance } = makeCtx(usPlan([FAIL_503, OK_US]));
  const t0 = clock.t;
  const first = await SD.loadIndexes(['us']);
  assert.equal(first.list.length, 0, 'fail-open: the failed read comes back empty');
  assert.equal(SD.indexRetryAt(['us']), t0 + TTL_NET, 'the failure window is visible to the consumer');

  const recovered = [];
  const rx = SD.indexRecovery(() => ['us'], (r) => recovered.push(plain(r)));
  assert.equal(rx.check(), true, 'check() reports an outstanding failure');
  assert.equal(timers.q.length, 1, 'exactly one re-ask is scheduled');

  await advance(TTL_NET - 1000);
  assert.equal(count(calls, US_INDEX), 1, 'no re-ask inside the failure window');
  assert.equal(recovered.length, 0);

  await advance(1000 + SLACK);
  assert.equal(count(calls, US_INDEX), 2, 'exactly one re-ask once the window closes');
  assert.equal(recovered.length, 1, 'onRecover runs with the fresh read');
  assert.deepEqual(recovered[0].list.map((x) => x.t), ['AAA', 'BBB']);
  assert.equal(SD.indexRetryAt(['us']), null, 'nothing left to recover');
  assert.equal(timers.q.length, 0, 'no timer survives a recovery');

  await advance(60 * 60 * 1000);
  assert.equal(count(calls, US_INDEX), 2, 'a recovered index is never re-read (no polling)');
});

test('Retry-After is honoured: the re-ask waits for the server-named window, not the 30 s default', async () => {
  const fail = { status: 503, body: {}, headers: { 'Retry-After': '120' } };
  const { SD, calls, clock, advance } = makeCtx(usPlan([fail, OK_US]));
  const t0 = clock.t;
  await SD.loadIndexes(['us']);
  assert.equal(SD.indexRetryAt(['us']), t0 + 120 * 1000);
  let n = 0;
  SD.indexRecovery(() => ['us'], () => { n += 1; }).check();
  await advance(TTL_NET + SLACK);
  assert.equal(count(calls, US_INDEX), 1, 'no re-ask at the 30 s default when Retry-After says 120 s');
  await advance(120 * 1000 - TTL_NET);
  assert.equal(count(calls, US_INDEX), 2, 're-asks once the Retry-After window closes');
  assert.equal(n, 1);
});

test('no polling: a timed re-ask that fails again is not re-timed — only page events re-ask after that', async () => {
  const { SD, calls, timers, doc, docBus, winBus, advance } = makeCtx(usPlan([FAIL_503]));
  await SD.loadIndexes(['us']);
  let n = 0;
  SD.indexRecovery(() => ['us'], () => { n += 1; }).check();
  await advance(TTL_NET + SLACK);
  assert.equal(count(calls, US_INDEX), 2, 'the one timed re-ask happened');
  assert.equal(timers.q.length, 0, 'a failed timed re-ask schedules nothing further');

  await advance(60 * 60 * 1000);
  assert.equal(count(calls, US_INDEX), 2, 'an hour of outage costs no further reads');

  doc.hidden = false;
  docBus.fire('visibilitychange');
  await flush();
  assert.equal(count(calls, US_INDEX), 3, 'the tab becoming visible re-asks');

  await advance(TTL_NET + SLACK);
  winBus.fire('online');
  await flush();
  assert.equal(count(calls, US_INDEX), 4, 'the network coming back re-asks');
  assert.equal(n, 0, 'onRecover never runs while the read keeps failing');
});

test('an event inside the failure window schedules the re-ask for when it closes instead of reading early', async () => {
  const { SD, calls, timers, winBus, advance } = makeCtx(usPlan([FAIL_503, FAIL_503, OK_US]));
  await SD.loadIndexes(['us']);
  const rx = SD.indexRecovery(() => ['us'], () => {});
  rx.check();
  await advance(TTL_NET + SLACK);            // timed re-ask fails → new window, not re-timed
  assert.equal(count(calls, US_INDEX), 2);
  assert.equal(timers.q.length, 0);
  winBus.fire('online');                      // inside the new window
  await flush();
  assert.equal(count(calls, US_INDEX), 2, 'no read inside the window');
  assert.equal(timers.q.length, 1, 'the event armed one re-ask for the window close');
  winBus.fire('online');
  assert.equal(timers.q.length, 1, 'a second event does not stack a second timer');
  await advance(TTL_NET + SLACK);
  assert.equal(count(calls, US_INDEX), 3);
  assert.equal(SD.indexRetryAt(['us']), null);
});

test('a hidden tab skips the timed re-ask; becoming visible re-asks', async () => {
  const { SD, calls, doc, docBus, advance } = makeCtx(usPlan([FAIL_503, OK_US]));
  await SD.loadIndexes(['us']);
  let n = 0;
  SD.indexRecovery(() => ['us'], () => { n += 1; }).check();
  doc.hidden = true;
  await advance(TTL_NET + SLACK);
  assert.equal(count(calls, US_INDEX), 1, 'no read while the tab is hidden');
  docBus.fire('visibilitychange');
  await flush();
  assert.equal(count(calls, US_INDEX), 1, 'a hide event never reads');
  doc.hidden = false;
  docBus.fire('visibilitychange');
  await flush();
  assert.equal(count(calls, US_INDEX), 2);
  assert.equal(n, 1);
});

test('offline skips the timed re-ask; the online event re-asks', async () => {
  const { SD, calls, nav, winBus, advance } = makeCtx(usPlan([FAIL_503, OK_US]));
  await SD.loadIndexes(['us']);
  let n = 0;
  SD.indexRecovery(() => ['us'], () => { n += 1; }).check();
  nav.onLine = false;
  await advance(TTL_NET + SLACK);
  assert.equal(count(calls, US_INDEX), 1, 'no read while offline');
  nav.onLine = true;
  winBus.fire('online');
  await flush();
  assert.equal(count(calls, US_INDEX), 2);
  assert.equal(n, 1);
});

test('no duplicate concurrent reads: events during an in-flight re-ask and a direct loader call share one fetch', async () => {
  const slow = deferred();
  const { SD, calls, docBus, winBus, advance } = makeCtx(usPlan([FAIL_503, () => slow.promise]));
  await SD.loadIndexes(['us']);
  let n = 0;
  SD.indexRecovery(() => ['us'], () => { n += 1; }).check();
  await advance(TTL_NET + SLACK);             // timed re-ask starts; the read hangs
  assert.equal(count(calls, US_INDEX), 2);
  docBus.fire('visibilitychange');
  winBus.fire('online');
  const direct = SD.loadIndexes(['us']);      // another caller on the same page
  await flush();
  assert.equal(count(calls, US_INDEX), 2, 'still ONE in-flight index read');
  slow.resolve(makeResponse(200, US_ROWS));
  const r = await direct;
  await flush();
  assert.equal(r.list.length, 2, 'the direct caller shares the recovered read');
  assert.equal(count(calls, US_INDEX), 2);
  assert.equal(n, 1);
});

test('nothing failed: check() wires no listener and schedules nothing', async () => {
  const { SD, calls, timers, docBus, winBus } = makeCtx(usPlan([OK_US]));
  await SD.loadIndexes(['us']);
  assert.equal(SD.indexRetryAt(['us']), null);
  const rx = SD.indexRecovery(() => ['us'], () => { throw new Error('must not run'); });
  assert.equal(rx.check(), false);
  assert.equal(timers.q.length, 0);
  assert.equal(docBus.count('visibilitychange'), 0);
  assert.equal(winBus.count('online'), 0);
  assert.equal(count(calls, US_INDEX), 1);
});

test('markets with different windows each get their own re-ask; onRecover runs only when one loads', async () => {
  let hkFails = true;
  let usFails = true;
  const route = (url) => {
    if (url === US_INDEX) {
      if (usFails) { usFails = false; return respond(503, {}); }
      return respond(200, US_ROWS);
    }
    if (url === HK_INDEX) {
      if (hkFails) { hkFails = false; return respond(429, {}, { 'Retry-After': '120' }); }
      return respond(200, HK_ROWS);
    }
    return respond(404, {});
  };
  const { SD, calls, clock, advance } = makeCtx(route);
  const t0 = clock.t;
  await SD.loadIndexes(['us', 'hk']);
  assert.equal(SD.indexRetryAt(['us', 'hk']), t0 + TTL_NET, 'earliest window wins');
  assert.equal(SD.indexRetryAt(['hk']), t0 + 120 * 1000);
  const seen = [];
  SD.indexRecovery(() => ['us', 'hk'], (r) => seen.push(plain(r).list.map((x) => x.t))).check();

  await advance(TTL_NET + SLACK);
  assert.equal(count(calls, US_INDEX), 2, 'US re-asked at its own window');
  assert.equal(count(calls, HK_INDEX), 1, 'HK not read inside its longer window');
  assert.deepEqual(seen, [['AAA', 'BBB']], 'partial recovery repaints with what loaded');

  await advance(120 * 1000 - TTL_NET);
  assert.equal(count(calls, HK_INDEX), 2, 'HK re-asked once its own window closes');
  assert.deepEqual(seen[1], ['AAA', 'BBB', '0700']);
  assert.equal(SD.indexRetryAt(['us', 'hk']), null);
});

test('a definitive 404 on a regional store waits its long window — no early re-read', async () => {
  const route = (url) => (url === US_INDEX ? respond(200, US_ROWS) : respond(404, {}));
  const { SD, calls, advance } = makeCtx(route);
  await SD.loadIndexes(['us', 'hk']);
  SD.indexRecovery(() => ['us', 'hk'], () => {}).check();
  await advance(9 * 60 * 1000);
  assert.equal(count(calls, HK_INDEX), 1, 'nothing inside the 10 min window');
  await advance(60 * 1000 + SLACK);
  assert.equal(count(calls, HK_INDEX), 2, 'one re-ask after the long window');
  await advance(60 * 60 * 1000);
  assert.equal(count(calls, HK_INDEX), 2, 'and no loop after it');
});

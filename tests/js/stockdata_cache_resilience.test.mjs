/**
 * Node replica of templates/stockdata.js index/ticker cache resilience (site20 S3).
 *
 * Five properties this suite pins, all inside the existing stockdata.js owner:
 *   S3-02  the US index is validated OFF TO THE SIDE and published atomically — a
 *          malformed payload (non-array top level, or non-object rows such as null)
 *          is never cached as success and never poisons the lookup; every object row
 *          is kept exactly as the pre-fix module kept it; list and byTicker always
 *          describe the same generation.
 *   S3-04  the US index read is deduplicated: direct callers (loadIndex) and indirect
 *          ones (loadIndexes(['us', ...])) share ONE in-flight fetch.
 *   S3-01  a FAILED regional index is never cached as success either — it is retried
 *          after a bounded window (short for transient failures / Retry-After, long
 *          for a definitive 404). Fail-open for the merge is preserved.
 *   S3-03  per-ticker negative entries classify the failure: transient (thrown fetch,
 *          5xx/408/429) gets the short TTL or the server's Retry-After clamped to
 *          [30 s, 10 min]; 404/410 and 401/403 keep the long TTL exactly as before.
 *   S3-05  a rich per-ticker payload is a success only when it carries the EXACT
 *          requested identity (`ticker`): another symbol's record, an error envelope
 *          or a non-object body is never cached as a positive success — it degrades
 *          through the existing null/30 s negative-TTL path. The search index keeps
 *          its own `t` shorthand on a different plane, and a legitimate LIMITED
 *          record (no price object, zero values, optional nulls) stays valid.
 *
 * The module runs in a `vm` context with a fake fetch, a mutable clock and no
 * browser. Set STOCKDATA_JS to run the same suite against another build of the
 * module (e.g. the pre-fix main version for red proofs).
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
// The real per-market router, loaded only by the cases that need a market store.
const BOOKS_PATH = join(ROOT, 'templates', 'market_books.js');

const US_INDEX = 'stockdata/index.json';
const HK_INDEX = 'hkstockdata/index.json';
const tickerUrl = (t) => `stockdata/${t}.json`;
const count = (calls, url) => calls.filter((u) => u === url).length;

// The module runs in a `vm` context, so arrays/objects it CONSTRUCTS are from another
// realm — their prototypes differ from this file's, and assert.deepEqual/strictEqual
// would fail on identical structure. JSON round-trips the value into this realm first.
const plain = (x) => JSON.parse(JSON.stringify(x));

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

// One fresh module instance per test: fake fetch + mutable clock, real Date.parse.
// `router: true` also loads the REAL market router (templates/market_books.js), so a
// per-market store is exercised instead of the US-only fallback.
function makeCtx(route, opts) {
  const clock = { t: 1700000000000 };
  const calls = [];
  const router = !!(opts && opts.router);
  const sandbox = {
    window: {},
    document: router
      ? { readyState: 'loading', documentElement: { getAttribute: () => 'en' }, addEventListener() {} }
      : { documentElement: { getAttribute: () => 'en' } },
    console,
    fetch: (url) => { calls.push(String(url)); return route(String(url)); },
    __clock: clock,
  };
  if (router) sandbox.localStorage = { getItem: () => null, setItem: () => {} };
  const ctx = vm.createContext(sandbox);
  vm.runInContext('Date.now = function () { return __clock.t; };', ctx);
  if (router) vm.runInContext(readFileSync(BOOKS_PATH, 'utf8'), ctx, { filename: 'market_books.js' });
  vm.runInContext(SOURCE, ctx);
  return { SD: sandbox.window.SD, MB: sandbox.window.MB, clock, calls };
}

const US_ROWS = [{ t: 'AAA', n: 'Alpha' }, { t: 'BBB', n: 'Beta' }];
const HK_ROWS = [{ t: '0700', n: 'Tencent' }, { t: '9988', n: 'Alibaba' }];

// ---------------------------------------------------------------- S3-02 ----

test('S3-02a: malformed index object rejects and is NOT cached as success — next call refetches', async () => {
  let bad = true;
  const route = (url) => {
    if (url === US_INDEX) {
      if (bad) { bad = false; return respond(200, { bad: 1 }); }
      return respond(200, US_ROWS);
    }
    return respond(404, {});
  };
  const { SD, calls } = makeCtx(route);
  await assert.rejects(() => SD.loadIndex(), /malformed index/);
  const res = await SD.loadIndex();
  assert.equal(count(calls, US_INDEX), 2, 'second loadIndex must perform a NEW fetch');
  assert.equal(Array.isArray(res.list), true, 'list must be the valid array, never the object');
  assert.equal(res.list.length, 2);
  assert.deepEqual(plain(res.list).map((x) => x.t), ['AAA', 'BBB']);
});

test('S3-02b: non-object rows (null, a primitive) are dropped from BOTH list and byTicker and do not poison the index', async () => {
  const raw = [{ t: 'AAA', n: 'A' }, null, 5, { t: 'BBB', n: null, s: null }];
  const { SD, calls } = makeCtx((url) => (url === US_INDEX ? respond(200, raw) : respond(404, {})));
  const res = await SD.loadIndex();
  assert.equal(res.list.length, 2);
  assert.deepEqual(Object.keys(res.byTicker).sort(), ['AAA', 'BBB']);
  res.list.forEach((row) => {
    assert.equal(row, res.byTicker[row.t], 'list row and byTicker entry are the same object');
    assert.equal(row.mkt, 'us');
  });
  assert.equal(res.byTicker.BBB.n, null, 'optional null fields are preserved as served');
  assert.equal(res.byTicker.BBB.s, null, 'optional null fields are preserved as served');
  await SD.loadIndex();
  assert.equal(count(calls, US_INDEX), 1, 'the cleaned index is a cached success');
});

test('S3-02c: valid empty index caches as success — no refetch on the second call', async () => {
  const { SD, calls } = makeCtx((url) => (url === US_INDEX ? respond(200, []) : respond(404, {})));
  const res = await SD.loadIndex();
  assert.deepEqual(plain(res.list), []);
  await SD.loadIndex();
  assert.equal(count(calls, US_INDEX), 1);
});

test('S3-02d: a cached success is immune to a later malformed response — no new fetch', async () => {
  let bad = false;
  const route = (url) => {
    if (url === US_INDEX) return bad ? respond(200, { bad: 1 }) : respond(200, US_ROWS);
    return respond(404, {});
  };
  const { SD, calls } = makeCtx(route);
  const first = await SD.loadIndex();
  bad = true;
  const second = await SD.loadIndex();
  assert.equal(count(calls, US_INDEX), 1);
  assert.equal(second.list, first.list);
  assert.equal(second.list.length, 2);
});

test('S3-02e: a row that already carries mkt keeps it', async () => {
  const raw = [{ t: 'BTC', mkt: 'crypto', n: 'Bitcoin' }];
  const { SD } = makeCtx((url) => (url === US_INDEX ? respond(200, raw) : respond(404, {})));
  const res = await SD.loadIndex();
  assert.equal(res.byTicker.BTC.mkt, 'crypto');
});

test('S3-02f preservation: every object row the pre-fix module kept survives — numeric, empty, null or missing t', async () => {
  const raw = [
    { t: 'AAA', n: 'Alpha' }, { t: 7203, n: 'num' }, { n: 'no-t' }, { t: '' }, { t: null },
  ];
  const { SD } = makeCtx((url) => (url === US_INDEX ? respond(200, raw) : respond(404, {})));
  const res = await SD.loadIndex();
  assert.equal(res.list.length, 5, 'no object row is dropped');
  assert.equal(res.byTicker['7203'].n, 'num', 'a numeric ticker is still looked up');
  assert.equal(res.byTicker.AAA.n, 'Alpha');
  res.list.forEach((row) => assert.equal(row.mkt, 'us'));
});

// ---------------------------------------------------------------- S3-04 ----

test('S3-04a: two concurrent loadIndex calls share one in-flight fetch and one result', async () => {
  const d = deferred();
  const route = (url) => (url === US_INDEX ? d.promise.then(() => makeResponse(200, US_ROWS)) : respond(404, {}));
  const { SD, calls } = makeCtx(route);
  const p1 = SD.loadIndex();
  const p2 = SD.loadIndex();
  d.resolve();
  const [r1, r2] = await Promise.all([p1, p2]);
  assert.equal(count(calls, US_INDEX), 1, 'exactly one US index fetch');
  assert.equal(r1.list, r2.list, 'same list object');
  assert.equal(r1.byTicker, r2.byTicker, 'same byTicker object');
  assert.equal(r1.list.length, 2);
});

test('S3-04b: concurrent loadIndex + loadIndexes(us,hk) share one US index fetch', async () => {
  const d = deferred();
  const route = (url) => {
    if (url === US_INDEX) return d.promise.then(() => makeResponse(200, US_ROWS));
    if (url === HK_INDEX) return respond(200, HK_ROWS);
    return respond(404, {});
  };
  const { SD, calls } = makeCtx(route);
  const p1 = SD.loadIndex();
  const p2 = SD.loadIndexes(['us', 'hk']);
  d.resolve();
  const [, merged] = await Promise.all([p1, p2]);
  assert.equal(count(calls, US_INDEX), 1, 'exactly one US index fetch');
  assert.ok(merged.byTicker.AAA, 'merged result contains the US rows');
  assert.equal(merged.byTicker.AAA.mkt, 'us');
});

test('S3-04c: a 503 rejects every concurrent waiter; the next call retries with a new fetch', async () => {
  let fail = true;
  const route = (url) => {
    if (url === US_INDEX) {
      if (fail) { fail = false; return respond(503); }
      return respond(200, US_ROWS);
    }
    return respond(404, {});
  };
  const { SD, calls } = makeCtx(route);
  const p1 = SD.loadIndex();
  const p2 = SD.loadIndex();
  await assert.rejects(() => p1);
  await assert.rejects(() => p2);
  assert.equal(count(calls, US_INDEX), 1, 'one fetch serves both waiters');
  const res = await SD.loadIndex();
  assert.equal(count(calls, US_INDEX), 2, 'the next call retries');
  assert.equal(res.list.length, 2);
});

test('S3-04d: cold call fetches once; warm call fetches zero more times', async () => {
  const { SD, calls } = makeCtx((url) => (url === US_INDEX ? respond(200, US_ROWS) : respond(404, {})));
  await SD.loadIndex();
  const cold = count(calls, US_INDEX);
  await SD.loadIndex();
  const warm = count(calls, US_INDEX) - cold;
  console.log('S3-04 cold/warm', cold, warm);
  assert.equal(cold, 1);
  assert.equal(warm, 0);
});

// ---------------------------------------------------------------- S3-01 ----

test('S3-01a: HK 503 is fail-open for the merge but NOT cached as success — refetch at +31s recovers rows', async () => {
  let hkFail = true;
  const route = (url) => {
    if (url === US_INDEX) return respond(200, US_ROWS);
    if (url === HK_INDEX) {
      if (hkFail) { hkFail = false; return respond(503); }
      return respond(200, HK_ROWS);
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  const m1 = await SD.loadIndexes(['us', 'hk']);
  assert.equal(m1.list.filter((x) => x.mkt === 'hk').length, 0, 'fail-open: no HK rows yet');
  assert.ok(m1.byTicker.AAA, 'US rows survive the HK failure');
  clock.t += 31000;
  const m2 = await SD.loadIndexes(['us', 'hk']);
  const hk = m2.list.filter((x) => x.mkt === 'hk');
  assert.equal(hk.length, 2, 'HK rows recovered');
  hk.forEach((x) => assert.equal(x.mkt, 'hk'));
  assert.equal(count(calls, HK_INDEX), 2, 'HK index was refetched, not replayed from the failure cache');
});

test('S3-01b: within the transient window a failed HK index is NOT refetched (no storm)', async () => {
  let hkFail = true;
  const route = (url) => {
    if (url === HK_INDEX) {
      if (hkFail) { hkFail = false; return respond(503); }
      return respond(200, HK_ROWS);
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  await SD.loadIndexes(['hk']);
  assert.equal(count(calls, HK_INDEX), 1);
  clock.t += 5000;
  const m = await SD.loadIndexes(['hk']);
  assert.deepEqual(plain(m.list), []);
  assert.equal(count(calls, HK_INDEX), 1, 'no refetch inside the negative window');
});

test('S3-01c: an empty index is a VALID success and is cached for the session (no refetch at +11 min)', async () => {
  const { SD, clock, calls } = makeCtx((url) => (url === HK_INDEX ? respond(200, []) : respond(404, {})));
  const m1 = await SD.loadIndexes(['hk']);
  assert.deepEqual(plain(m1.list), []);
  clock.t += 11 * 60 * 1000;
  await SD.loadIndexes(['hk']);
  assert.equal(count(calls, HK_INDEX), 1, 'a successful empty book is not retried');
});

test('S3-01d preservation: two concurrent loadIndexes(hk) share one in-flight HK fetch', async () => {
  const d = deferred();
  const route = (url) => (url === HK_INDEX ? d.promise.then(() => makeResponse(200, HK_ROWS)) : respond(404, {}));
  const { SD, calls } = makeCtx(route);
  const p1 = SD.loadIndexes(['hk']);
  const p2 = SD.loadIndexes(['hk']);
  d.resolve();
  const [r1, r2] = await Promise.all([p1, p2]);
  assert.equal(count(calls, HK_INDEX), 1, 'one HK fetch serves both callers');
  assert.equal(r1.list.length, 2);
  assert.equal(r2.list.length, 2);
});

test('S3-01e: US index 503 via loadIndexes(us) — empty now, refetched at +31s', async () => {
  let usFail = true;
  const route = (url) => {
    if (url === US_INDEX) {
      if (usFail) { usFail = false; return respond(503); }
      return respond(200, US_ROWS);
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  const m1 = await SD.loadIndexes(['us']);
  assert.equal(m1.list.length, 0);
  clock.t += 31000;
  const m2 = await SD.loadIndexes(['us']);
  assert.equal(count(calls, US_INDEX), 2, 'US index refetched after the transient window');
  assert.equal(m2.list.length, 2);
  assert.equal(m2.byTicker.AAA.mkt, 'us');
});

test('S3-01f: HK 503 with Retry-After 120 — no refetch at +60s, refetch at +121s', async () => {
  let hkFail = true;
  const route = (url) => {
    if (url === HK_INDEX) {
      if (hkFail) { hkFail = false; return respond(503, {}, { 'Retry-After': '120' }); }
      return respond(200, HK_ROWS);
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  const m1 = await SD.loadIndexes(['hk']);
  assert.deepEqual(plain(m1.list), []);
  clock.t += 60000;
  await SD.loadIndexes(['hk']);
  assert.equal(count(calls, HK_INDEX), 1, 'server asked for 120 s — honour it');
  clock.t += 61000;
  const m2 = await SD.loadIndexes(['hk']);
  assert.equal(count(calls, HK_INDEX), 2, 'refetch after the Retry-After window');
  assert.equal(m2.list.length, 2);
});

test('S3-01g: HK 404 — no refetch at +60s, refetch at +10 min + 1s', async () => {
  let hkGone = true;
  const route = (url) => {
    if (url === HK_INDEX) {
      if (hkGone) { hkGone = false; return respond(404, {}); }
      return respond(200, HK_ROWS);
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  const m1 = await SD.loadIndexes(['hk']);
  assert.deepEqual(plain(m1.list), []);
  clock.t += 60000;
  await SD.loadIndexes(['hk']);
  assert.equal(count(calls, HK_INDEX), 1, 'a definitive 404 keeps the long window');
  clock.t += 10 * 60 * 1000 + 1000;
  const m2 = await SD.loadIndexes(['hk']);
  assert.equal(count(calls, HK_INDEX), 2);
  assert.equal(m2.list.length, 2);
});

test('S3-01h: HK 200 with a malformed body — empty for the merge, refetched at +31s', async () => {
  let bad = true;
  const route = (url) => {
    if (url === HK_INDEX) {
      if (bad) { bad = false; return respond(200, { bad: 1 }); }
      return respond(200, HK_ROWS);
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  const m1 = await SD.loadIndexes(['us', 'hk']);
  assert.equal(m1.list.filter((x) => x.mkt === 'hk').length, 0);
  clock.t += 31000;
  const m2 = await SD.loadIndexes(['us', 'hk']);
  assert.equal(m2.list.filter((x) => x.mkt === 'hk').length, 2);
  assert.equal(count(calls, HK_INDEX), 2, 'malformed payload was not cached as success');
});

// ---------------------------------------------------------------- S3-03 ----

test('S3-03a: ticker 503 — null now, one new fetch at +31s resolves the object', async () => {
  let fail = true;
  const route = (url) => {
    if (url === tickerUrl('AAA')) {
      if (fail) { fail = false; return respond(503); }
      return respond(200, { ticker: 'AAA' });
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  assert.equal(count(calls, tickerUrl('AAA')), 1);
  clock.t += 31000;
  const j = await SD.loadTicker('AAA');
  assert.deepEqual(plain(j), { ticker: 'AAA' });
  assert.equal(count(calls, tickerUrl('AAA')), 2, 'exactly one new fetch after the transient window');
});

test('S3-03b: ticker 404 — long TTL: no fetch at +31s, refetch at +10 min + 1s', async () => {
  let gone = true;
  const route = (url) => {
    if (url === tickerUrl('AAA')) {
      if (gone) { gone = false; return respond(404, {}); }
      return respond(200, { ticker: 'AAA' });
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  clock.t += 31000;
  assert.equal(await SD.loadTicker('AAA'), null);
  assert.equal(count(calls, tickerUrl('AAA')), 1, '404 keeps the long window');
  clock.t += 10 * 60 * 1000 + 1000;
  await SD.loadTicker('AAA');
  assert.equal(count(calls, tickerUrl('AAA')), 2);
});

test('S3-03c: ticker 503 with Retry-After 120 — no fetch at +60s, fetch at +121s', async () => {
  let fail = true;
  const route = (url) => {
    if (url === tickerUrl('AAA')) {
      if (fail) { fail = false; return respond(503, {}, { 'Retry-After': '120' }); }
      return respond(200, { ticker: 'AAA' });
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  clock.t += 60000;
  assert.equal(await SD.loadTicker('AAA'), null);
  assert.equal(count(calls, tickerUrl('AAA')), 1);
  clock.t += 61000;
  await SD.loadTicker('AAA');
  assert.equal(count(calls, tickerUrl('AAA')), 2);
});

test('S3-03d: ticker 503 with Retry-After 5 — floored to 30 s: no fetch at +10s, fetch at +31s', async () => {
  let fail = true;
  const route = (url) => {
    if (url === tickerUrl('AAA')) {
      if (fail) { fail = false; return respond(503, {}, { 'Retry-After': '5' }); }
      return respond(200, { ticker: 'AAA' });
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  clock.t += 10000;
  assert.equal(await SD.loadTicker('AAA'), null);
  assert.equal(count(calls, tickerUrl('AAA')), 1, 'a 5 s Retry-After must not storm');
  clock.t += 21000;
  await SD.loadTicker('AAA');
  assert.equal(count(calls, tickerUrl('AAA')), 2);
});

test('S3-03e: ticker 503 with an HTTP-date Retry-After (+120 s) — no fetch at +60s, fetch at +121s', async () => {
  let fail = true;
  const at = new Date(1700000000000 + 120000).toUTCString();
  const route = (url) => {
    if (url === tickerUrl('AAA')) {
      if (fail) { fail = false; return respond(503, {}, { 'Retry-After': at }); }
      return respond(200, { ticker: 'AAA' });
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  clock.t += 60000;
  assert.equal(await SD.loadTicker('AAA'), null);
  assert.equal(count(calls, tickerUrl('AAA')), 1);
  clock.t += 61000;
  await SD.loadTicker('AAA');
  assert.equal(count(calls, tickerUrl('AAA')), 2);
});

test('S3-03f: 429 retries short; 403 and 401 keep the long TTL and never resolve data', async () => {
  const state = { 429: false, 403: false, 401: false };
  const statusOf = (t) => (t === 'AAA' ? 429 : t === 'BBB' ? 403 : 401);
  const route = (url) => {
    for (const t of ['AAA', 'BBB', 'CCC']) {
      if (url === tickerUrl(t)) {
        if (state[statusOf(t)]) return respond(200, { ticker: t });
        state[statusOf(t)] = true;
        return respond(statusOf(t), {});
      }
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  assert.equal(await SD.loadTicker('BBB'), null);
  assert.equal(await SD.loadTicker('CCC'), null);
  clock.t += 31000;
  await SD.loadTicker('AAA');
  assert.equal(count(calls, tickerUrl('AAA')), 2, '429 gets the short TTL');
  assert.equal(count(calls, tickerUrl('BBB')), 1, '403 gets the long TTL');
  assert.equal(count(calls, tickerUrl('CCC')), 1, '401 gets the long TTL');
  clock.t += 10 * 60 * 1000 + 1000;
  assert.deepEqual(plain(await SD.loadTicker('BBB')), { ticker: 'BBB' });
  assert.deepEqual(plain(await SD.loadTicker('CCC')), { ticker: 'CCC' });
  assert.equal(count(calls, tickerUrl('BBB')), 2);
  assert.equal(count(calls, tickerUrl('CCC')), 2);
});

test('S3-03g: a huge Retry-After (999999 s) is capped at 10 min — fetch at +10 min + 1s', async () => {
  let fail = true;
  const route = (url) => {
    if (url === tickerUrl('AAA')) {
      if (fail) { fail = false; return respond(503, {}, { 'Retry-After': '999999' }); }
      return respond(200, { ticker: 'AAA' });
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  clock.t += 60000;
  assert.equal(await SD.loadTicker('AAA'), null);
  assert.equal(count(calls, tickerUrl('AAA')), 1);
  clock.t += 541000; // now t0 + 10 min + 1 s
  await SD.loadTicker('AAA');
  assert.equal(count(calls, tickerUrl('AAA')), 2, 'the cap opens the window at 10 min');
});

test('S3-03h preservation: after the failure window expires, three concurrent calls share one fetch', async () => {
  let failed = false;
  let d = null;
  const route = (url) => {
    if (url === tickerUrl('AAA')) {
      if (!failed) { failed = true; return respond(503); }
      if (!d) d = deferred();
      return d.promise.then(() => makeResponse(200, { ticker: 'AAA' }));
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  clock.t += 10 * 60 * 1000 + 1000; // past BOTH the short and the long window
  const p1 = SD.loadTicker('AAA');
  const p2 = SD.loadTicker('AAA');
  const p3 = SD.loadTicker('AAA');
  await Promise.resolve();
  d.resolve();
  const [r1, r2, r3] = await Promise.all([p1, p2, p3]);
  assert.deepEqual(plain(r1), { ticker: 'AAA' });
  assert.equal(r2, r1);
  assert.equal(r3, r1);
  assert.equal(count(calls, tickerUrl('AAA')), 2, 'one refetch serves all three waiters');
});

test('S3-03i: loadTickers degrades exactly the failed row and resolves the batch', async () => {
  const route = (url) => {
    if (url === tickerUrl('AAA')) return respond(200, { ticker: 'AAA' });
    if (url === tickerUrl('BBB')) return respond(503);
    if (url === tickerUrl('CCC')) return respond(200, { ticker: 'CCC' });
    return respond(404, {});
  };
  const { SD } = makeCtx(route);
  const seen = {};
  await SD.loadTickers(['AAA', 'BBB', 'CCC'], (t, j) => { seen[t] = j; });
  assert.deepEqual(plain(seen.AAA), { ticker: 'AAA' });
  assert.deepEqual(plain(seen.CCC), { ticker: 'CCC' });
  assert.equal(seen.BBB, null);
});

test('S3-03j: a thrown fetch gets the short TTL — null now, one new fetch at +31s', async () => {
  const route = (url) => (url === tickerUrl('AAA') ? Promise.reject(new TypeError('net')) : respond(404, {}));
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  clock.t += 31000;
  assert.equal(await SD.loadTicker('AAA'), null);
  assert.equal(count(calls, tickerUrl('AAA')), 2, 'network errors are retried after 30 s');
});

// ---------------------------------------- S3-05: rich per-ticker identity ----
//
// The loader accepted ANY successfully parsed 200 body as the rich record for the
// symbol that was asked for: another symbol's record, an error envelope, a bare
// array, a string or a null body all became a POSITIVE cached success for the
// requested name and were served for the rest of the session. The rich per-ticker
// identity is `ticker` — the five library builders emit it on ordinary AND LIMITED
// records — while the search index keeps the `t` shorthand on a DIFFERENT plane,
// untouched by this guard.
//
// These cases pin ONE guard: a rich payload is accepted only when it carries the
// EXACT requested identity. Anything else degrades to null through the EXISTING
// catch / 30 s negative-TTL path — no new cache, no new retry owner, no new
// entitlement plane, no alias table, no price/field requirement. A legitimate
// record (a LIMITED record with no price object, a zero price, optional nulls) is
// accepted and cached exactly as before.

// The rich record lives in the market's own store; `=`/`^` become `_` in the
// filename (stockdata.js safeTicker). The search index is a different plane.
const richUrl = (dir, t) => `${dir}/${String(t).replace(/[=^]/g, '_')}.json`;

const MALFORMED_RICH = [
  ['null body', null],
  ['empty array', []],
  ['array of records', [{ ticker: 'AAA' }]],
  ['empty object', {}],
  ['error envelope', { error: 'temporarily unavailable' }],
  ['string body', 'temporarily unavailable'],
  ['boolean body', false],
  ['numeric body', 0],
  ['non-string ticker', { ticker: 123 }],
  ['another symbol', { ticker: 'BBB', tech: { price: 900 } }],
  ['search-index shorthand only', { t: 'AAA', tech: { price: 900 } }],
];

for (const [name, bad] of MALFORMED_RICH) {
  test(`S3-05a: a 200 body that is not this ticker's rich record (${name}) is not a success`, async () => {
    let healthy = false;
    const route = (url) => (url === tickerUrl('AAA')
      ? respond(200, healthy ? { ticker: 'AAA', tech: { price: 42 } } : bad)
      : respond(404, {}));
    const { SD, clock, calls } = makeCtx(route);
    assert.equal(await SD.loadTicker('AAA'), null, 'a malformed 200 must not reach the caller');
    healthy = true;
    clock.t += 5000;
    assert.equal(await SD.loadTicker('AAA'), null, 'the existing short failure window still holds');
    assert.equal(count(calls, tickerUrl('AAA')), 1, 'no retry storm inside the window');
    clock.t += 26000;
    const recovered = await SD.loadTicker('AAA');
    assert.equal(recovered.ticker, 'AAA');
    assert.equal(recovered.tech.price, 42);
    assert.equal(count(calls, tickerUrl('AAA')), 2, 'one read after the existing short window');
  });
}

test('S3-05b: the exact requested identity is served and session-cached, for every symbol spelling', async () => {
  for (const symbol of ['AAA', 'DX=F', '^GSPC', 'BRK-B', '0700.HK', '7203.T', '600519.SS', 'RY.TO']) {
    const good = { ticker: symbol, limited: true, ladder: { state: 'LIMITED' }, tech: { price: 0 }, optional: null };
    const { SD, calls } = makeCtx(() => respond(200, good));
    const got = await SD.loadTicker(symbol);
    assert.deepEqual(plain(got), plain(good), 'the rich record is served verbatim');
    assert.equal(got.tech.price, 0, 'a zero price is a legitimate value');
    assert.equal(got.optional, null, 'optional nulls survive');
    assert.equal(await SD.loadTicker(symbol), got, 'a valid record is session-cached');
    assert.equal(calls.length, 1, 'exactly one read');
    assert.equal(calls[0], richUrl('stockdata', symbol), 'the filename keeps the existing sanitization');
  }
});

test('S3-05c: three concurrent asks share one malformed read and one rejection', async () => {
  const d = deferred();
  let healthy = false;
  const route = (url) => {
    if (url !== tickerUrl('AAA')) return respond(404, {});
    if (healthy) return respond(200, { ticker: 'AAA' });
    return d.promise.then(() => makeResponse(200, { ticker: 'BBB' }));
  };
  const { SD, clock, calls } = makeCtx(route);
  const waits = [SD.loadTicker('AAA'), SD.loadTicker('AAA'), SD.loadTicker('AAA')];
  d.resolve();
  assert.deepEqual(await Promise.all(waits), [null, null, null], 'one rejection serves every waiter');
  assert.equal(count(calls, tickerUrl('AAA')), 1, 'exactly one read');
  healthy = true;
  clock.t += 31000;
  const recovered = await Promise.all([SD.loadTicker('AAA'), SD.loadTicker('AAA')]);
  assert.equal(recovered[0].ticker, 'AAA');
  assert.equal(recovered[0], recovered[1], 'one recovery read serves both waiters');
  assert.equal(count(calls, tickerUrl('AAA')), 2);
});

test('S3-05d: a wrong-identity row degrades to null and never relabels another ticker', async () => {
  const route = (url) => {
    if (url === tickerUrl('AAA')) return respond(200, { ticker: 'BBB', tech: { price: 900 } });
    if (url === tickerUrl('CCC')) return respond(200, { ticker: 'CCC', tech: { price: 2 } });
    return respond(404, {});
  };
  const { SD, calls } = makeCtx(route);
  const seen = {};
  await SD.loadTickers(['AAA', 'CCC'], (t, j) => { seen[t] = j; });
  assert.equal(seen.AAA, null, 'the mismatched row degrades to null');
  assert.equal(seen.CCC.ticker, 'CCC', 'the valid peer keeps its own identity');
  assert.equal(seen.CCC.tech.price, 2);
  assert.equal(count(calls, tickerUrl('AAA')), 1);
  assert.equal(count(calls, tickerUrl('CCC')), 1);
});

test('S3-05e: a legitimate LIMITED record with no price object is accepted — no invented schema requirement', async () => {
  const good = {
    ticker: 'AAA', name: 'Alpha', sector: 'Tech', asof: '2026-11-04', listed: '2026-11-02',
    history_days: 3, limited: true, ladder: { state: 'LIMITED' },
  };
  const { SD, calls } = makeCtx(() => respond(200, good));
  const got = await SD.loadTicker('AAA');
  assert.deepEqual(plain(got), plain(good));
  assert.equal(Object.hasOwn(got, 'tech'), false, 'no price object is required');
  assert.equal(got.ladder.state, 'LIMITED');
  assert.equal(got.history_days, 3);
  assert.equal(await SD.loadTicker('AAA'), got, 'the valid record is session-cached');
  assert.equal(calls.length, 1);
});

test('S3-05f: the search index keeps its `t` shorthand — the rich guard does not touch the index plane', async () => {
  const { SD } = makeCtx((url) => (url === US_INDEX ? respond(200, US_ROWS) : respond(404, {})));
  const res = await SD.loadIndex();
  assert.deepEqual(plain(res.list).map((x) => x.t), ['AAA', 'BBB']);
  assert.equal(res.byTicker.AAA.n, 'Alpha');
  assert.equal(Object.hasOwn(res.byTicker.AAA, 'ticker'), false, 'index rows keep the `t` shorthand');
});

// ---- the five library producers (docket #8757) -------------------------------
//
// The guard reads ONE field: `ticker`. These cases pin that field against the
// producers that own the rich records, so a future producer change cannot silently
// flip the identity key (or reintroduce the `t` shorthand) without this suite going
// red. The record SHAPE is extracted from each producer's own `_limited_rec`
// source, so the fixture cannot drift from the contract it claims to model; only
// the VALUES are synthetic — no frozen production payload is asserted here.
const PRODUCERS = [
  { market: 'us', file: 'scripts/build_stock_library.py', dir: 'stockdata', symbols: ['IPO', 'BRK-B', 'DX=F', '^GSPC'] },
  { market: 'cn', file: 'scripts/build_china_library.py', dir: 'chinastockdata', symbols: ['600519.SS', '000001.SZ', '830001.BJ'] },
  { market: 'hk', file: 'scripts/build_hk_library.py', dir: 'hkstockdata', symbols: ['0700.HK', '0005.HK', '9999.HK'] },
  { market: 'ca', file: 'scripts/build_canada_library.py', dir: 'canadastockdata', symbols: ['RY.TO', 'GIB-A.TO', 'SAMPLE.V'] },
  { market: 'intl', file: 'scripts/build_intl_library.py', dir: 'intlstockdata', symbols: ['7203.T', 'ASML.AS', 'VOD.L', '005930.KS', 'SAMPLE.SW'] },
];

// The source of one top-level Python function (from its `def` to the next
// column-0 statement).
function pythonDefBlock(text, name) {
  const m = new RegExp(`^def ${name}\\(`, 'm').exec(text);
  if (!m) return null;
  const lines = text.slice(m.index).split('\n');
  const out = [lines[0]];
  for (let i = 1; i < lines.length; i++) {
    if (/^\S/.test(lines[i])) break;
    out.push(lines[i]);
  }
  return out.join('\n');
}

// The top-level keys of the dict literal a function returns. Depth-aware, so a
// NESTED literal (the `ladder`: {"state": "LIMITED"} of every producer, HK's
// `chart`) never contributes its own keys; string-aware, so a value is never
// mistaken for a key.
function dictLiteralKeys(block) {
  const at = block.indexOf('return {');
  if (at < 0) return null;
  let i = at + 'return '.length;
  const keys = [];
  let depth = 0;
  let expectKey = true;
  while (i < block.length) {
    const ch = block[i];
    if (ch === '{' || ch === '[' || ch === '(') { depth++; i++; continue; }
    if (ch === '}' || ch === ']' || ch === ')') {
      depth--;
      i++;
      if (depth === 0) break;
      continue;
    }
    if (ch === '"' || ch === "'") {
      const quote = ch;
      let j = i + 1;
      let text = '';
      while (j < block.length) {
        if (block[j] === '\\') { text += block[j] + block[j + 1]; j += 2; continue; }
        if (block[j] === quote) break;
        text += block[j];
        j++;
      }
      const after = j + 1;
      if (expectKey && depth === 1) {
        let k = after;
        while (k < block.length && /\s/.test(block[k])) k++;
        if (block[k] === ':') { keys.push(text); expectKey = false; }
      }
      i = after;
      continue;
    }
    if (ch === ',') { if (depth === 1) expectKey = true; i++; continue; }
    i++;
  }
  return keys;
}

let _contracts = null;
function producerContracts() {
  if (_contracts) return _contracts;
  _contracts = PRODUCERS.map((p) => {
    const text = readFileSync(join(ROOT, p.file), 'utf8');
    const block = pythonDefBlock(text, '_limited_rec');
    assert.ok(block, `${p.file} must still define _limited_rec`);
    const keys = dictLiteralKeys(block);
    assert.ok(Array.isArray(keys) && keys.length, `${p.file} _limited_rec must still return a dict literal`);
    return { ...p, keys, source: text };
  });
  return _contracts;
}

// A synthetic record with exactly the producer's own top-level key set. The
// VALUES are placeholders; the SHAPE is the producer's.
function limitedRecord(symbol, keys) {
  const rec = {};
  for (const k of keys) {
    switch (k) {
      case 'ticker': rec[k] = symbol; break;
      case 'name': rec[k] = 'Synthetic issuer'; break;
      case 'sector': rec[k] = 'Test sector'; break;
      case 'tv': rec[k] = symbol; break;
      case 'asof': rec[k] = '2026-11-04'; break;
      case 'listed': rec[k] = '2026-11-02'; break;
      case 'history_days': rec[k] = 3; break;
      case 'limited': rec[k] = true; break;
      case 'ladder': rec[k] = { state: 'LIMITED' }; break;
      case 'chart': rec[k] = { t: ['2026-11-02', '2026-11-03', '2026-11-04'], c: [10, 0, 12.126], anchor: { era: 'SYNTHETIC_TEST_ANCHOR', b3: [0] } }; break;
      case 'flag': rec[k] = 'TEST'; break;
      case 'market': rec[k] = 'TEST'; break;
      default: rec[k] = null; break;   // an unknown optional field stays null — still a legal record
    }
  }
  return rec;
}

test('S3-05g: every library producer emits the rich identity key `ticker` and never the index shorthand `t`', () => {
  for (const p of producerContracts()) {
    assert.ok(p.keys.includes('ticker'), `${p.file} _limited_rec must emit the rich identity key "ticker"`);
    assert.equal(p.keys.includes('t'), false, `${p.file} _limited_rec must not emit the index shorthand "t"`);
    assert.ok(p.keys.includes('limited'), `${p.file} _limited_rec must keep the LIMITED contract`);
    assert.ok(p.keys.includes('ladder'), `${p.file} _limited_rec must keep the ladder sentinel`);
    assert.ok(/"t":/.test(p.source), `${p.file} must still emit search-index rows with the "t" shorthand`);
  }
});

test('S3-05h: a legitimate LIMITED record from every library producer is served from its own market store', async () => {
  for (const p of producerContracts()) {
    for (const symbol of p.symbols) {
      const rec = limitedRecord(symbol, p.keys);
      const { SD, MB, calls } = makeCtx(() => respond(200, rec), { router: true });
      assert.equal(MB.storeOf(symbol), p.dir, `${symbol} routes to ${p.dir}`);
      const got = await SD.loadTicker(symbol);
      assert.deepEqual(plain(got), plain(rec), `${p.market} ${symbol}: the producer record is served verbatim`);
      assert.equal(Object.hasOwn(got, 'tech'), false, `${p.market} ${symbol}: a LIMITED record needs no price object`);
      assert.equal(got.ladder.state, 'LIMITED');
      assert.equal(await SD.loadTicker(symbol), got, `${p.market} ${symbol}: the valid record is session-cached`);
      assert.deepEqual(calls, [richUrl(p.dir, symbol)], `${p.market} ${symbol}: one read from its own store`);
    }
  }
});

for (const p of PRODUCERS) {
  for (const symbol of p.symbols) {
    for (const fault of ['another ticker', 'index shorthand only']) {
      test(`S3-05i: the ${p.market} producer record for ${symbol} is rejected when it carries ${fault}, then recovers`, async () => {
        const contract = producerContracts().find((c) => c.market === p.market);
        const rec = limitedRecord(symbol, contract.keys);
        const bad = plain(rec);
        if (fault === 'another ticker') bad.ticker = 'WRONG-IDENTITY';
        else { bad.t = bad.ticker; delete bad.ticker; }
        let healthy = false;
        const { SD, clock, calls } = makeCtx(() => respond(200, healthy ? rec : bad), { router: true });
        assert.equal(await SD.loadTicker(symbol), null, 'never deliver a different or missing rich identity');
        healthy = true;
        clock.t += 29000;
        assert.equal(await SD.loadTicker(symbol), null, 'the existing short failure window still holds');
        assert.equal(calls.length, 1, 'no retry storm inside the window');
        clock.t += 2000;
        const recovered = await SD.loadTicker(symbol);
        assert.deepEqual(plain(recovered), plain(rec), 'the same producer payload recovers');
        assert.equal(calls.length, 2, 'one read after the existing short window');
      });
    }
  }
}

test('S3-05j: a five-store batch isolates one wrong identity and preserves every valid peer', async () => {
  const contracts = producerContracts();
  const picks = ['IPO', '600519.SS', '0700.HK', 'RY.TO', '7203.T'];
  const recs = {};
  const byUrl = {};
  for (const p of contracts) {
    const symbol = picks.find((s) => p.symbols.includes(s));
    if (!symbol) continue;
    recs[symbol] = limitedRecord(symbol, p.keys);
    byUrl[richUrl(p.dir, symbol)] = recs[symbol];
  }
  byUrl[richUrl('hkstockdata', '0700.HK')] = { ...recs['0700.HK'], ticker: '9999.HK' };
  const { SD, calls } = makeCtx((url) => respond(200, byUrl[url]), { router: true });
  const seen = {};
  await SD.loadTickers(picks, (t, j) => { seen[t] = j; }, { concurrency: 2 });
  assert.equal(calls.length, 5, 'one read per requested symbol');
  assert.equal(seen['0700.HK'], null, 'the mismatched row degrades to null');
  for (const symbol of picks.filter((s) => s !== '0700.HK')) {
    assert.deepEqual(plain(seen[symbol]), plain(recs[symbol]), `${symbol} keeps its own record`);
  }
});

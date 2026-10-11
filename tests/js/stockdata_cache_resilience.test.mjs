/**
 * Node replica of templates/stockdata.js index/ticker cache resilience (site20 S3).
 *
 * Four properties this suite pins, all inside the existing stockdata.js owner:
 *   S3-02  the US index is validated OFF TO THE SIDE and published atomically — a
 *          malformed payload (non-array top level, rows with no usable ticker `t`)
 *          is never cached as success; list and byTicker always describe the same
 *          generation.
 *   S3-04  the US index read is deduplicated: direct callers (loadIndex) and indirect
 *          ones (loadIndexes(['us', ...])) share ONE in-flight fetch.
 *   S3-01  a FAILED regional index is never cached as success either — it is retried
 *          after a bounded window (short for transient failures / Retry-After, long
 *          for a definitive 404). Fail-open for the merge is preserved.
 *   S3-03  per-ticker negative entries classify the failure: transient (thrown fetch,
 *          5xx/408/429) gets the short TTL or the server's Retry-After clamped to
 *          [30 s, 10 min]; 404/410 and 401/403 keep the long TTL exactly as before.
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
function makeCtx(route) {
  const clock = { t: 1700000000000 };
  const calls = [];
  const sandbox = {
    window: {},
    document: { documentElement: { getAttribute: () => 'en' } },
    console,
    fetch: (url) => { calls.push(String(url)); return route(String(url)); },
    __clock: clock,
  };
  const ctx = vm.createContext(sandbox);
  vm.runInContext('Date.now = function () { return __clock.t; };', ctx);
  vm.runInContext(SOURCE, ctx);
  return { SD: sandbox.window.SD, clock, calls };
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

test('S3-02b: rows without a usable ticker t are dropped from BOTH list and byTicker', async () => {
  const raw = [
    { t: 'AAA', n: 'A' }, null, 5, { n: 'no-t' }, { t: '' }, { t: null },
    { t: 'BBB', n: null, s: null },
  ];
  const { SD } = makeCtx((url) => (url === US_INDEX ? respond(200, raw) : respond(404, {})));
  const res = await SD.loadIndex();
  assert.equal(res.list.length, 2);
  assert.deepEqual(Object.keys(res.byTicker).sort(), ['AAA', 'BBB']);
  res.list.forEach((row) => {
    assert.equal(row, res.byTicker[row.t], 'list row and byTicker entry are the same object');
    assert.equal(row.mkt, 'us');
  });
  assert.equal(res.byTicker.BBB.n, null, 'optional null fields are preserved as served');
  assert.equal(res.byTicker.BBB.s, null, 'optional null fields are preserved as served');
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
      return respond(200, { t: 'AAA' });
    }
    return respond(404, {});
  };
  const { SD, clock, calls } = makeCtx(route);
  assert.equal(await SD.loadTicker('AAA'), null);
  assert.equal(count(calls, tickerUrl('AAA')), 1);
  clock.t += 31000;
  const j = await SD.loadTicker('AAA');
  assert.deepEqual(plain(j), { t: 'AAA' });
  assert.equal(count(calls, tickerUrl('AAA')), 2, 'exactly one new fetch after the transient window');
});

test('S3-03b: ticker 404 — long TTL: no fetch at +31s, refetch at +10 min + 1s', async () => {
  let gone = true;
  const route = (url) => {
    if (url === tickerUrl('AAA')) {
      if (gone) { gone = false; return respond(404, {}); }
      return respond(200, { t: 'AAA' });
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
      return respond(200, { t: 'AAA' });
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
      return respond(200, { t: 'AAA' });
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
      return respond(200, { t: 'AAA' });
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
        if (state[statusOf(t)]) return respond(200, { t });
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
  assert.deepEqual(plain(await SD.loadTicker('BBB')), { t: 'BBB' });
  assert.deepEqual(plain(await SD.loadTicker('CCC')), { t: 'CCC' });
  assert.equal(count(calls, tickerUrl('BBB')), 2);
  assert.equal(count(calls, tickerUrl('CCC')), 2);
});

test('S3-03g: a huge Retry-After (999999 s) is capped at 10 min — fetch at +10 min + 1s', async () => {
  let fail = true;
  const route = (url) => {
    if (url === tickerUrl('AAA')) {
      if (fail) { fail = false; return respond(503, {}, { 'Retry-After': '999999' }); }
      return respond(200, { t: 'AAA' });
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
      return d.promise.then(() => makeResponse(200, { t: 'AAA' }));
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
  assert.deepEqual(plain(r1), { t: 'AAA' });
  assert.equal(r2, r1);
  assert.equal(r3, r1);
  assert.equal(count(calls, tickerUrl('AAA')), 2, 'one refetch serves all three waiters');
});

test('S3-03i: loadTickers degrades exactly the failed row and resolves the batch', async () => {
  const route = (url) => {
    if (url === tickerUrl('AAA')) return respond(200, { t: 'AAA' });
    if (url === tickerUrl('BBB')) return respond(503);
    if (url === tickerUrl('CCC')) return respond(200, { t: 'CCC' });
    return respond(404, {});
  };
  const { SD } = makeCtx(route);
  const seen = {};
  await SD.loadTickers(['AAA', 'BBB', 'CCC'], (t, j) => { seen[t] = j; });
  assert.deepEqual(plain(seen.AAA), { t: 'AAA' });
  assert.deepEqual(plain(seen.CCC), { t: 'CCC' });
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

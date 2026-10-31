'use strict';
/* Regression checks for the actual templates/theme.js account loader.
   Every behavioural case executes the ACTUAL canonical shared-theme loader from disk in a
   fresh node:vm sandbox (no copied or mocked re-implementation of it), driven
   by fake timers, a fake DOM document and a fake promise; two extra cases use
   a real native Promise to prove the duck-typed ready.then integration.
   Run with:  node PROGRESSIVE_LOADER_TEST.cjs */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert');

const FILE = path.join(__dirname, '..', 'templates', 'theme.js');
const SOURCE = fs.readFileSync(FILE, 'utf8');
const START = SOURCE.indexOf('(function loadAccount() {');
assert(START >= 0, 'canonical shared account loader missing');
assert.equal(SOURCE.indexOf('(function loadAccount() {', START + 1), -1, 'duplicate shared loader');
const END = SOURCE.indexOf('\n})();', START);
assert(END > START, 'canonical shared loader boundary missing');
const CODE = SOURCE.slice(START, END + '\n})();'.length);
const MM_DEFAULT = 'https://app.mastermind-x.com';
const RELEASE_KEY = 'account.js?v=20261018-shared-shell-source-join';

/* ---- fakes ------------------------------------------------------------- */
function makeTimers() {
  let seq = 0;
  let now = 0;
  const live = new Map();
  return {
    setTimeout(fn, ms) { const id = ++seq; live.set(id, { fn: fn, at: now + (ms || 0) }); return id; },
    clearTimeout(id) { live.delete(id); },
    advance(delta) {
      now += delta;
      for (;;) {
        const due = Array.from(live.entries())
          .filter((e) => e[1].at <= now)
          .sort((a, b) => a[1].at - b[1].at);
        if (due.length === 0) return;
        live.delete(due[0][0]);
        due[0][1].fn();
      }
    },
    get pending() { return live.size; }
  };
}

function makeDocument() {
  const listeners = { pointerdown: [], keydown: [] };
  const doc = {
    scripts: [],
    head: { appendChild(node) { doc.scripts.push(node); } },
    createElement(tag) { return { tagName: String(tag).toUpperCase(), src: null, async: undefined }; },
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    removeEventListener(type, fn) {
      const l = listeners[type];
      if (l) listeners[type] = l.filter((f) => f !== fn);
    },
    dispatch(type) { (listeners[type] || []).slice().forEach((fn) => fn({ type: type })); }
  };
  doc.listenerCount = (type) => (listeners[type] || []).length;
  return doc;
}

/* Fake promise: then() registers handlers, resolve/reject fire them once. */
function fakeDeferred() {
  const d = { settled: false, onOk: null, onErr: null };
  d.ready = { then: function (onOk, onErr) { d.onOk = onOk; d.onErr = onErr; return d.ready; } };
  d.resolve = function (v) { if (!d.settled) { d.settled = true; if (d.onOk) d.onOk(v); } };
  d.reject = function (e) { if (!d.settled) { d.settled = true; if (d.onErr) d.onErr(e); } };
  return d;
}

/* Fresh vm sandbox; runs the actual replacement file exactly once per case. */
function boot(opts) {
  const o = opts || {};
  const timers = makeTimers();
  const doc = makeDocument();
  const sb = {
    setTimeout: timers.setTimeout,
    clearTimeout: timers.clearTimeout,
    document: doc,
    _mmSharedAssetRoot: o.root !== undefined ? o.root : '/themes/shared/'
  };
  sb.window = sb;
  if (o.mmApi !== undefined) sb.MM_API = o.mmApi;
  if (o.loading) sb.__mmAccountLoading = true;
  if ('boot' in o) sb.MDX_PROGRESSIVE_BOOT = o.boot;
  vm.runInContext(CODE, vm.createContext(sb), { filename: FILE, displayErrors: true });
  return { sb: sb, doc: doc, timers: timers };
}

const scripts = (doc) => doc.scripts.filter((s) => s.tagName === 'SCRIPT');
const inputListeners = (doc) => doc.listenerCount('pointerdown') + doc.listenerCount('keydown');

/* ---- runner ------------------------------------------------------------ */
let passed = 0;
const failed = [];
async function test(name, fn) {
  try {
    await fn();
    passed += 1;
    process.stdout.write('ok   ' + name + '\n');
  } catch (e) {
    failed.push(name);
    process.stdout.write('FAIL ' + name + '\n     ' + (e && e.message ? e.message : String(e)) + '\n');
  }
}

(async function main() {
  await test('static: replacement carries the full contract and stays <=100 lines', () => {
    const lines = CODE.replace(/\s+$/, '').split('\n');
    assert.ok(lines.length <= 100, 'replacement must be <=100 lines, got ' + lines.length);
    ['__mmAccountLoading', 'MDX_PROGRESSIVE_BOOT', RELEASE_KEY, "'" + MM_DEFAULT + "'",
      '_mmSharedAssetRoot', 'pointerdown', 'keydown', '1500'].forEach((need) => {
      assert.ok(CODE.indexOf(need) !== -1, 'missing required token: ' + need);
    });
    ['localStorage', 'sessionStorage', 'document.cookie', 'XMLHttpRequest', 'indexedDB', 'fetch(']
      .forEach((banned) => {
        assert.strictEqual(CODE.indexOf(banned), -1, 'forbidden token present: ' + banned);
      });
  });

  await test('default: no MDX_PROGRESSIVE_BOOT -> original loader runs immediately', () => {
    const env = boot({ root: '/basket_canada/themes/' });
    const got = scripts(env.doc);
    assert.strictEqual(got.length, 1, 'expected exactly one script tag');
    assert.strictEqual(got[0].src, '/basket_canada/themes/' + RELEASE_KEY, 'exact sourceurl');
    assert.strictEqual(got[0].async, true);
    assert.strictEqual(env.sb.__mmAccountLoading, true);
    assert.strictEqual(env.sb.MM_API, MM_DEFAULT);
    assert.strictEqual(env.timers.pending, 0, 'no timer armed in default mode');
    assert.strictEqual(inputListeners(env.doc), 0, 'no listeners armed in default mode');
  });

  await test('default: boot without a ready.then -> still immediate', () => {
    [{}, { ready: null }, { ready: {} }, { ready: { then: 'nope' } }, true].forEach((b) => {
      const env = boot({ boot: b });
      assert.strictEqual(scripts(env.doc).length, 1, 'boot=' + JSON.stringify(b));
      assert.strictEqual(env.timers.pending, 0);
      assert.strictEqual(inputListeners(env.doc), 0);
    });
  });

  await test('singleton: pre-set __mmAccountLoading short-circuits both modes', () => {
    const plain = boot({ loading: true });
    assert.strictEqual(plain.doc.scripts.length, 0);
    assert.strictEqual(plain.timers.pending, 0);
    const deferred = boot({ loading: true, boot: { ready: fakeDeferred().ready } });
    assert.strictEqual(deferred.doc.scripts.length, 0, 'guard must short-circuit before arming');
    assert.strictEqual(deferred.timers.pending, 0);
    assert.strictEqual(inputListeners(deferred.doc), 0);
  });

  await test('deferred: boot arms 1500ms timer + both input listeners, loads nothing yet', () => {
    const env = boot({ boot: { ready: fakeDeferred().ready } });
    assert.strictEqual(env.sb.__mmAccountLoading, true, 'singleton claimed synchronously');
    assert.strictEqual(env.doc.scripts.length, 0, 'nothing loaded while deferring');
    assert.strictEqual(env.timers.pending, 1);
    assert.strictEqual(env.doc.listenerCount('pointerdown'), 1);
    assert.strictEqual(env.doc.listenerCount('keydown'), 1);
  });

  await test('release: ready resolution triggers the original loader exactly once', () => {
    const d = fakeDeferred();
    const env = boot({ root: '/rotation/themes/', boot: { ready: d.ready } });
    d.resolve({ account: 'typed-finance-settled' });
    const got = scripts(env.doc);
    assert.strictEqual(got.length, 1);
    assert.strictEqual(got[0].src, '/rotation/themes/' + RELEASE_KEY, 'exact sourceurl');
    assert.strictEqual(got[0].async, true);
    assert.strictEqual(env.sb.MM_API, MM_DEFAULT);
    assert.strictEqual(env.timers.pending, 0, 'timer removed on release');
    assert.strictEqual(inputListeners(env.doc), 0, 'listeners removed on release');
  });

  await test('release: ready rejection also triggers the original loader once', () => {
    const d = fakeDeferred();
    const env = boot({ boot: { ready: d.ready } });
    d.reject(new Error('typed finance failed'));
    assert.strictEqual(scripts(env.doc).length, 1);
    assert.strictEqual(env.timers.pending, 0);
    assert.strictEqual(inputListeners(env.doc), 0);
  });

  await test('release: 1500ms bounded fallback fires when ready never settles', () => {
    const env = boot({ root: '/basket/themes/', boot: { ready: fakeDeferred().ready } });
    env.timers.advance(1499);
    assert.strictEqual(env.doc.scripts.length, 0, 'must not release before 1500ms');
    assert.strictEqual(env.timers.pending, 1);
    env.timers.advance(1);
    const got = scripts(env.doc);
    assert.strictEqual(got.length, 1);
    assert.strictEqual(got[0].src, '/basket/themes/' + RELEASE_KEY, 'exact sourceurl');
    assert.strictEqual(env.timers.pending, 0);
    assert.strictEqual(inputListeners(env.doc), 0);
  });

  await test('release: first pointerdown input triggers the loader and cleans up', () => {
    const env = boot({ boot: { ready: fakeDeferred().ready } });
    env.doc.dispatch('pointerdown');
    assert.strictEqual(scripts(env.doc).length, 1);
    assert.strictEqual(env.timers.pending, 0);
    assert.strictEqual(inputListeners(env.doc), 0);
  });

  await test('release: first keydown input triggers the loader and cleans up', () => {
    const env = boot({ boot: { ready: fakeDeferred().ready } });
    env.doc.dispatch('keydown');
    assert.strictEqual(scripts(env.doc).length, 1);
    assert.strictEqual(env.timers.pending, 0);
    assert.strictEqual(inputListeners(env.doc), 0);
  });

  await test('exactly-once: ready + timer + repeated inputs together still load once', () => {
    const d = fakeDeferred();
    const env = boot({ boot: { ready: d.ready } });
    env.doc.dispatch('pointerdown');
    env.doc.dispatch('keydown');
    d.resolve({});
    env.timers.advance(10000);
    env.doc.dispatch('keydown');
    assert.strictEqual(scripts(env.doc).length, 1, 'loader must fire exactly once');
    assert.strictEqual(env.timers.pending, 0);
  });

  await test('retained: existing MM_API is never overwritten in either mode', () => {
    const plain = boot({ mmApi: 'https://staging.example' });
    assert.strictEqual(plain.sb.MM_API, 'https://staging.example');
    const d = fakeDeferred();
    const env = boot({ mmApi: 'https://staging.example', boot: { ready: d.ready } });
    d.resolve({});
    assert.strictEqual(env.sb.MM_API, 'https://staging.example');
  });

  await test('real Promise: native ready resolution releases the loader', async () => {
    let resolveReady;
    const env = boot({ boot: { ready: new Promise((res) => { resolveReady = res; }) } });
    assert.strictEqual(env.doc.scripts.length, 0);
    resolveReady({ ok: true });
    await new Promise((r) => setImmediate(r));
    assert.strictEqual(scripts(env.doc).length, 1);
    assert.strictEqual(env.timers.pending, 0);
    assert.strictEqual(inputListeners(env.doc), 0);
  });

  await test('real Promise: native ready rejection releases the loader', async () => {
    let rejectReady;
    const env = boot({ boot: { ready: new Promise((res, rej) => { rejectReady = rej; }) } });
    assert.strictEqual(env.doc.scripts.length, 0);
    rejectReady(new Error('ready rejected'));
    await new Promise((r) => setImmediate(r));
    assert.strictEqual(scripts(env.doc).length, 1);
    assert.strictEqual(inputListeners(env.doc), 0);
  });

  process.stdout.write('\n' + passed + ' passed, ' + failed.length + ' failed\n');
  if (failed.length) {
    process.stdout.write('FAILED: ' + failed.join(' | ') + '\n');
    process.exitCode = 1;
  }
})().catch((e) => {
  console.error('harness error:', e);
  process.exitCode = 1;
});

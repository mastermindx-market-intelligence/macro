/**
 * Generation fence + ticker identity for templates/stockbrief.js (S4-04).
 *
 * Loads the real module into a fresh node:vm context per test. Override the
 * source with STOCKBRIEF_JS (resolved against process.cwd()) to replay red on
 * old bytes.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';
import vm from 'node:vm';

function sourcePath() {
  if (process.env.STOCKBRIEF_JS) return resolve(process.cwd(), process.env.STOCKBRIEF_JS);
  return new URL('../../templates/stockbrief.js', import.meta.url);
}

const SRC = readFileSync(sourcePath(), 'utf8');

function escapeDiv(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function nvdaBrief(extra) {
  return {
    schema: 'catalyst_stock.v1',
    ticker: 'NVDA',
    name: 'NVIDIA Corp',
    summary: 'NVDA-NEW <b>chips</b> & co',
    drivers: ['d1'],
    risks: ['r1'],
    catalysts: ['c1'],
    confidence: 'medium',
    model: 'm',
    asof: '2026-10-09',
    zh: { summary: '英伟达-新', drivers: ['驱1'] },
    ...extra,
  };
}

function aaplBrief(extra) {
  return {
    schema: 'catalyst_stock.v1',
    ticker: 'AAPL',
    name: 'Apple Inc',
    summary: 'APPLE-OLD',
    drivers: ['d1'],
    risks: ['r1'],
    catalysts: ['c1'],
    confidence: 'low',
    model: 'm',
    asof: '2026-10-09',
    ...extra,
  };
}

async function flush() {
  await new Promise((r) => setImmediate(r));
}

async function flush3() {
  await flush();
  await flush();
  await flush();
}

function harness() {
  const panel = { style: { display: 'none' } };
  const body = { innerHTML: '' };
  let lang = 'en';
  const listeners = {};
  const pending = [];

  function fetch(url) {
    return new Promise((resolve, reject) => {
      pending.push({
        url,
        resolve,
        reject,
        ok(brief) {
          resolve({ ok: true, json: async () => brief });
        },
        notFound() {
          resolve({
            ok: false,
            json: async () => {
              throw new Error('no body');
            },
          });
        },
        badJson() {
          resolve({
            ok: true,
            json: async () => {
              throw new SyntaxError('bad');
            },
          });
        },
      });
    });
  }

  const document = {
    getElementById(id) {
      if (id === 'stock-brief') return panel;
      if (id === 'stock-brief-body') return body;
      return null;
    },
    createElement() {
      let text = '';
      return {
        set textContent(v) {
          text = v == null ? '' : String(v);
        },
        get textContent() {
          return text;
        },
        get innerHTML() {
          return escapeDiv(text);
        },
      };
    },
    documentElement: {
      getAttribute(name) {
        return name === 'data-lang' ? lang : null;
      },
    },
    addEventListener(type, fn) {
      (listeners[type] ||= []).push(fn);
    },
  };

  const window = {};
  const context = vm.createContext({
    window,
    document,
    fetch,
    Date,
    String,
    Array,
    Object,
    encodeURIComponent,
  });
  vm.runInContext(SRC, context);

  return {
    panel,
    body,
    pending,
    window,
    setLang(v) {
      lang = v;
    },
    fire(type) {
      for (const fn of listeners[type] || []) fn();
    },
    last() {
      return pending[pending.length - 1];
    },
  };
}

test('S4-04 late prior-ticker success cannot replace current brief', async () => {
  const h = harness();
  h.window.loadStockBrief('AAPL');
  await flush3();
  h.window.loadStockBrief('NVDA');
  await flush3();
  assert.equal(h.pending.length, 2);
  h.pending[1].ok(nvdaBrief());
  await flush3();
  assert.equal(h.panel.style.display, '');
  assert.match(h.body.innerHTML, /NVDA-NEW &lt;b&gt;chips&lt;\/b&gt; &amp; co/);
  h.pending[0].ok(aaplBrief());
  await flush3();
  assert.equal(h.panel.style.display, '');
  assert.match(h.body.innerHTML, /NVDA-NEW/);
  assert.doesNotMatch(h.body.innerHTML, /APPLE-OLD/);
});

test('S4-04 prior 404 cannot hide a newer success', async () => {
  const h = harness();
  h.window.loadStockBrief('AAPL');
  await flush3();
  h.window.loadStockBrief('NVDA');
  await flush3();
  h.pending[1].ok(nvdaBrief());
  await flush3();
  assert.equal(h.panel.style.display, '');
  assert.match(h.body.innerHTML, /NVDA-NEW/);
  h.pending[0].notFound();
  await flush3();
  assert.equal(h.panel.style.display, '');
  assert.match(h.body.innerHTML, /NVDA-NEW/);
});

test('S4-04 prior network error cannot hide a newer success (preserve)', async () => {
  const h = harness();
  h.window.loadStockBrief('AAPL');
  await flush3();
  h.window.loadStockBrief('NVDA');
  await flush3();
  h.pending[1].ok(nvdaBrief());
  await flush3();
  assert.equal(h.panel.style.display, '');
  h.pending[0].reject(new Error('network'));
  await flush3();
  assert.equal(h.panel.style.display, '');
  assert.match(h.body.innerHTML, /NVDA-NEW/);
});

test('S4-04 langchange renders only the active brief', async () => {
  const h = harness();
  h.window.loadStockBrief('AAPL');
  await flush3();
  h.window.loadStockBrief('NVDA');
  await flush3();
  h.pending[0].ok(aaplBrief());
  await flush3();
  assert.equal(h.panel.style.display, 'none');
  assert.doesNotMatch(h.body.innerHTML, /APPLE-OLD/);
  h.fire('langchange');
  assert.equal(h.panel.style.display, 'none');
  assert.doesNotMatch(h.body.innerHTML, /APPLE-OLD/);
  h.pending[1].ok(nvdaBrief());
  await flush3();
  assert.equal(h.panel.style.display, '');
  assert.match(h.body.innerHTML, /NVDA-NEW/);
  h.setLang('zh');
  h.fire('langchange');
  assert.match(h.body.innerHTML, /英伟达-新/);
  assert.doesNotMatch(h.body.innerHTML, /APPLE-OLD/);
});

test('S4-04 identity-mismatched brief stays unavailable', async () => {
  const h = harness();
  h.window.loadStockBrief('NVDA');
  await flush3();
  h.last().ok(aaplBrief());
  await flush3();
  assert.equal(h.panel.style.display, 'none');
  assert.equal(h.body.innerHTML, '');
});

test('S4-04 unavailable response carries no prior-company content', async () => {
  async function afterAaplThen(apply) {
    const h = harness();
    h.window.loadStockBrief('AAPL');
    await flush3();
    h.last().ok(aaplBrief());
    await flush3();
    assert.equal(h.panel.style.display, '');
    assert.match(h.body.innerHTML, /APPLE-OLD/);
    h.window.loadStockBrief('NVDA');
    await flush3();
    apply(h.last());
    await flush3();
    assert.equal(h.panel.style.display, 'none');
    assert.equal(h.body.innerHTML, '');
  }
  await afterAaplThen((p) => p.notFound());
  await afterAaplThen((p) => p.badJson());
  await afterAaplThen((p) => p.ok(null));
  await afterAaplThen((p) => p.ok([1]));
  await afterAaplThen((p) => p.ok('x'));
});

test('S4-04 safe-name identity mapping (preserve)', async () => {
  const h1 = harness();
  h1.window.loadStockBrief('GC_F');
  await flush3();
  h1.last().ok({
    ticker: 'GC=F',
    name: 'Gold',
    summary: 'gold-ok',
    drivers: ['d'],
  });
  await flush3();
  assert.equal(h1.panel.style.display, '');
  assert.match(h1.body.innerHTML, /gold-ok/);

  const h2 = harness();
  h2.window.loadStockBrief('_VIX');
  await flush3();
  h2.last().ok({
    ticker: '^VIX',
    name: 'VIX',
    summary: 'vix-ok',
    drivers: ['d'],
  });
  await flush3();
  assert.equal(h2.panel.style.display, '');
  assert.match(h2.body.innerHTML, /vix-ok/);

  const h3 = harness();
  h3.window.loadStockBrief('NVDA');
  await flush3();
  const noTicker = nvdaBrief();
  delete noTicker.ticker;
  h3.last().ok(noTicker);
  await flush3();
  assert.equal(h3.panel.style.display, '');
  assert.match(h3.body.innerHTML, /NVDA-NEW/);
});

test('S4-04 escaping (preserve)', async () => {
  const h = harness();
  h.window.loadStockBrief('NVDA');
  await flush3();
  h.last().ok(nvdaBrief({ summary: '<img src=x onerror=alert(1)>' }));
  await flush3();
  assert.match(h.body.innerHTML, /&lt;img/);
  assert.doesNotMatch(h.body.innerHTML, /<img/);
});

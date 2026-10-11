/**
 * Zoom y-bounds: missing observations (S4-01) and hidden traces (S4-02).
 *
 * Loads the real module into a fresh node:vm context per test. Override the
 * source with CHARTS_JS (resolved against process.cwd()) to replay red on old
 * bytes.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';
import vm from 'node:vm';

function sourcePath() {
  if (process.env.CHARTS_JS) return resolve(process.cwd(), process.env.CHARTS_JS);
  return new URL('../../templates/charts.js', import.meta.url);
}

const SRC = readFileSync(sourcePath(), 'utf8');
const TOL = 1e-9;
const XS2 = ['2024-01-01', '2024-06-01'];
const XS3 = ['2024-01-01', '2024-06-01', '2024-12-01'];
const X0 = '2024-01-01';
const X1 = '2024-12-31';

function padded(vals) {
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  let pad = (hi - lo) * 0.08;
  if (!(pad > 0)) pad = Math.abs(hi) * 0.08 || 1;
  return [lo - pad, hi + pad];
}

function assertRange(actual, expected, msg) {
  assert.ok(actual, msg || 'expected a range');
  assert.equal(actual.length, 2, msg);
  assert.ok(
    Math.abs(actual[0] - expected[0]) < TOL,
    `${msg || 'lo'}: ${actual[0]} vs ${expected[0]}`,
  );
  assert.ok(
    Math.abs(actual[1] - expected[1]) < TOL,
    `${msg || 'hi'}: ${actual[1]} vs ${expected[1]}`,
  );
}

function finiteValues(obj) {
  const out = [];
  if (obj == null || typeof obj !== 'object') return out;
  for (const v of Object.values(obj)) {
    if (Array.isArray(v)) {
      for (const x of v) if (typeof x === 'number') out.push(x);
    }
  }
  return out;
}

async function flush() {
  await new Promise((r) => setImmediate(r));
}

async function flush3() {
  await flush();
  await flush();
  await flush();
}

function makeGd({ layout = {}, data = [] } = {}) {
  const handlers = {};
  layout.xaxis = layout.xaxis || {};
  const gd = {
    layout,
    data,
    _fullData: data,
    handlers,
    on(ev, fn) {
      (handlers[ev] ||= []).push(fn);
    },
  };
  return gd;
}

function loadModule(gds) {
  const relayoutCalls = [];
  const loadListeners = [];
  const windowObj = {
    Plotly: {
      relayout(_gd, upd) {
        relayoutCalls.push(upd);
        return Promise.resolve();
      },
    },
    addEventListener(t, fn) {
      loadListeners.push(fn);
    },
  };
  const document = {
    readyState: 'complete',
    querySelectorAll: () => gds,
    addEventListener() {},
  };
  const context = vm.createContext({
    window: windowObj,
    document,
    Object,
    Math,
    Array,
    Date,
    Number,
    isFinite,
    Infinity,
    NaN,
  });
  vm.runInContext(SRC, context);
  return {
    relayoutCalls,
    fireLoad() {
      for (const fn of loadListeners) fn();
    },
  };
}

async function zoom(gd, a, b) {
  gd.layout.xaxis.range = [a, b];
  const hs = gd.handlers.plotly_relayout || [];
  for (const fn of hs) fn({ 'xaxis.range[0]': a, 'xaxis.range[1]': b });
  await flush3();
}

async function restyle(gd, update, idx, opts = {}) {
  const requireListener = opts.requireListener !== false;
  const hs = gd.handlers.plotly_restyle || [];
  if (requireListener && !hs.length) {
    throw new Error('no plotly_restyle listener');
  }
  for (const fn of hs) fn([update, idx]);
  await flush3();
}

function last(calls) {
  return calls[calls.length - 1];
}

test('S4-01 null observation adds no synthetic zero', async () => {
  const gd = makeGd({
    layout: {},
    data: [{ x: XS3, y: [100, null, 101] }],
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101]));
});

test('S4-01 empty, whitespace and boolean observations are excluded', async () => {
  const gd = makeGd({
    layout: {},
    data: [{ x: ['2024-01-01', '2024-03-01', '2024-05-01', '2024-07-01', '2024-09-01', '2024-11-01'], y: [100, '', 101, '  ', true, false] }],
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101]));
});

test('S4-01 real zero stays a valid bound (preserve)', async () => {
  const gd = makeGd({
    layout: {},
    data: [{ x: XS2, y: [0, 5] }],
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([0, 5]));
});

test('S4-01 finite numeric strings still count (preserve)', async () => {
  const gd = makeGd({
    layout: {},
    data: [{ x: XS2, y: ['100', '101'] }],
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101]));
});

test('S4-01 independent axes use only their own observations', async () => {
  const gd = makeGd({
    layout: { yaxis2: {} },
    data: [
      { x: XS3, y: [100, null, 101] },
      { x: XS2, y: [5, 6], yaxis: 'y2' },
    ],
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  const upd = last(h.relayoutCalls);
  assertRange(upd['yaxis.range'], padded([100, 101]));
  assertRange(upd['yaxis2.range'], padded([5, 6]));
});

test('S4-01 fixed axis untouched (preserve)', async () => {
  const gd = makeGd({
    layout: { yaxis2: { autorange: false, range: [-1, 1] } },
    data: [
      { x: XS2, y: [10, 11] },
      { x: XS3, y: [0.2, null, 0.3], yaxis: 'y2' },
    ],
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  const upd = last(h.relayoutCalls);
  assert.ok(!Object.prototype.hasOwnProperty.call(upd, 'yaxis2.range'));
  assertRange(upd['yaxis.range'], padded([10, 11]));
});

test('S4-01 all-missing window degrades honestly', async () => {
  const gd1 = makeGd({
    layout: {},
    data: [{ x: XS3, y: [null, null, ''] }],
  });
  const h1 = loadModule([gd1]);
  await zoom(gd1, X0, X1);
  assert.equal(h1.relayoutCalls.length, 0);

  const gd2 = makeGd({
    layout: { yaxis2: {} },
    data: [
      { x: XS3, y: [null, null, ''] },
      { x: XS2, y: [5, 6], yaxis: 'y2' },
    ],
  });
  const h2 = loadModule([gd2]);
  await zoom(gd2, X0, X1);
  assert.equal(h2.relayoutCalls.length, 1);
  const upd = last(h2.relayoutCalls);
  assert.ok(!Object.prototype.hasOwnProperty.call(upd, 'yaxis.range'));
  assertRange(upd['yaxis2.range'], padded([5, 6]));
});

test('S4-02 legendonly trace excluded', async () => {
  const gd = makeGd({
    layout: {},
    data: [
      { x: XS2, y: [100, 101] },
      { x: XS2, y: [1000, 1000], visible: 'legendonly' },
    ],
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101]));
});

test('S4-02 visible:false trace excluded', async () => {
  const gd = makeGd({
    layout: {},
    data: [
      { x: XS2, y: [100, 101] },
      { x: XS2, y: [1000, 1000], visible: false },
    ],
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101]));
});

test('S4-02 showing a trace reintroduces its values exactly once', async () => {
  const data = [
    { x: XS2, y: [100, 101], visible: true },
    { x: XS2, y: [1000, 1000], visible: 'legendonly' },
  ];
  const gd = makeGd({ layout: {}, data });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  assert.equal(h.relayoutCalls.length, 1);
  data[1].visible = true;
  await restyle(gd, { visible: [true] }, [1]);
  assert.equal(h.relayoutCalls.length, 2);
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101, 1000]));
});

test('S4-02 hiding a trace via restyle rescales to the remaining visible data', async () => {
  const data = [
    { x: XS2, y: [100, 101], visible: true },
    { x: XS2, y: [1000, 1000], visible: true },
  ];
  const gd = makeGd({ layout: {}, data });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101, 1000]));
  const n = h.relayoutCalls.length;
  data[1].visible = 'legendonly';
  await restyle(gd, { visible: ['legendonly'] }, [1]);
  assert.equal(h.relayoutCalls.length, n + 1);
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101]));
});

test('S4-02 restyle before any rescale leaves Plotly autorange alone (preserve)', async () => {
  const data = [
    { x: XS2, y: [100, 101], visible: true },
    { x: XS2, y: [1000, 1000], visible: 'legendonly' },
  ];
  const gd = makeGd({ layout: {}, data });
  const h = loadModule([gd]);
  data[1].visible = true;
  await restyle(gd, { visible: [true] }, [1], { requireListener: false });
  assert.equal(h.relayoutCalls.length, 0);
});

test('S4-02 non-visibility restyle is ignored (preserve)', async () => {
  const gd = makeGd({
    layout: {},
    data: [{ x: XS2, y: [100, 101] }],
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  const n = h.relayoutCalls.length;
  await restyle(gd, { 'line.color': ['red'] }, [0], { requireListener: false });
  assert.equal(h.relayoutCalls.length, n);
});

test('S4-02 listeners attach exactly once', async () => {
  const gd = makeGd({
    layout: {},
    data: [{ x: XS2, y: [100, 101] }],
  });
  const h = loadModule([gd]);
  h.fireLoad();
  h.fireLoad();
  assert.equal(gd.handlers.plotly_relayout.length, 1);
  assert.equal(gd.handlers.plotly_restyle.length, 1);
});

test('S4-02 multi-axis with fixed axis', async () => {
  const data = [
    { x: XS2, y: [100, 101], visible: true },
    { x: XS2, y: [1000, 1000], visible: 'legendonly' },
    { x: XS2, y: [0.2, 0.3], yaxis: 'y2', visible: true },
  ];
  const gd = makeGd({
    layout: { yaxis2: { autorange: false, range: [-1, 1] } },
    data,
  });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  for (const upd of h.relayoutCalls) {
    assert.ok(!Object.prototype.hasOwnProperty.call(upd, 'yaxis2.range'));
  }
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101]));
  data[1].visible = true;
  await restyle(gd, { visible: [true] }, [1]);
  for (const upd of h.relayoutCalls) {
    assert.ok(!Object.prototype.hasOwnProperty.call(upd, 'yaxis2.range'));
  }
  assertRange(last(h.relayoutCalls)['yaxis.range'], padded([100, 101, 1000]));
});

test('S4-02 empty visible population yields no invalid range', async () => {
  const data = [
    { x: XS2, y: [100, 101], visible: true },
    { x: XS2, y: [1000, 1000], visible: true },
  ];
  const gd = makeGd({ layout: {}, data });
  const h = loadModule([gd]);
  await zoom(gd, X0, X1);
  const n = h.relayoutCalls.length;
  data[0].visible = 'legendonly';
  data[1].visible = 'legendonly';
  await restyle(gd, { visible: ['legendonly'] }, [0, 1]);
  assert.equal(h.relayoutCalls.length, n, 'empty visible population must not relayout');
  for (const upd of h.relayoutCalls) {
    for (const v of finiteValues(upd)) {
      assert.ok(Number.isFinite(v), `non-finite ${v}`);
    }
  }
});

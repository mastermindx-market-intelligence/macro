/* Execute the real globe, vendored geometry, and topology with deterministic
 * browser scheduling. These tests exercise behavior, not source-text patterns. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');

class Element {
  constructor() {
    this.attrs = {}; this.listeners = {}; this.nodes = {}; this.hidden = false;
    this.style = { setProperty(name, value) { this[name] = value; } };
    const classes = new Set();
    this.classList = { add: (...xs) => xs.forEach(x => classes.add(x)),
      remove: (...xs) => xs.forEach(x => classes.delete(x)), contains: x => classes.has(x),
      toggle(x, value) { value = value === undefined ? !classes.has(x) : value; value ? classes.add(x) : classes.delete(x); return value; } };
    this.rect = { width: 1100, height: 500, left: 0, top: 0 };
    this.offsetWidth = 280; this.offsetHeight = 260; this.textContent = '';
  }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k] ?? null; }
  removeAttribute(k) { delete this.attrs[k]; }
  addEventListener(k, fn) { (this.listeners[k] ||= []).push(fn); }
  emit(k, extra = {}) { for (const fn of this.listeners[k] || []) fn({ preventDefault() {}, stopPropagation() {}, ...extra }); }
  getBoundingClientRect() { return this.rect; }
  setPointerCapture() {}
  focus() { this.focusCount = (this.focusCount || 0) + 1; }
  appendChild(el) { el.parentNode = this; }
  querySelector(k) {
    if (this.nodes[k]) return this.nodes[k];
    if (this.innerHTML?.includes(k.slice(1))) return this.nodes[k] = new Element();
    return null;
  }
  querySelectorAll() { return []; }
  set innerHTML(value) { this._html = value; this.nodes = {}; }
  get innerHTML() { return this._html || ''; }
}

async function scene(options = {}) {
  let now = 100, nextId = 1, requests = 0, rejectNext = !!options.rejectFetch;
  const frames = new Map(), timeouts = new Map(), intervals = new Map();
  const stage = new Element(), canvas = new Element(), deck = new Element(), tip = new Element();
  const rootEl = new Element(), document = new Element(), win = new Element();
  rootEl.setAttribute('data-theme', 'dark'); rootEl.setAttribute('data-lang', 'en');
  const controls = ['motion', 'reset', 'zoom-out', 'zoom-in', 'tour', 'routes'].map(action => {
    const el = new Element(); el.setAttribute('data-gd-action', action); return el;
  });
  const retry = new Element(); retry.setAttribute('data-gd-action', 'retry');
  const data = [{ cc: 'US', kind: 'country', geo_ids: ['840'], quad: 'q1', flag: 'US',
    name_en: 'United States', name_zh: '美国', index_sym: '^GSPC', index_price: '100', index_chg_pct: 1,
    quad_name_en: 'Goldilocks', quad_name_zh: '理想增长', index_name_en: 'S&P 500', index_name_zh: '标普500',
    risk_text_en: 'calm', risk_text_zh: '平静', confidence: .8, href: 'macro.html',
    tz: 'America/New_York', open: '09:30', close: '16:00', agrees_with: [] }];
  const leg = new Element(); leg.setAttribute('data-cc', 'US');
  deck.nodes = { '.gd-status': new Element(), '[data-gd-action="retry"]': retry, '.gd-route-note': new Element() };
  deck.querySelectorAll = selector => selector === '.gd-leg' ? [leg] :
    selector === '.gd-leg, .gd-controls button' ? [leg, ...controls] :
    selector === '[data-gd-action]' ? [...controls, retry] : controls;
  stage.nodes = { '.gd-canvas': canvas, '.gd-tip': tip, '#gd-live': new Element(),
    '.gd-isl-front': new Element(), '.gd-isl-back': new Element() };
  stage.closest = () => deck;
  const context = () => new Proxy({ fillStyle: '#000000', measureText: () => ({ width: 30 }),
    createRadialGradient: () => ({ addColorStop() {} }), createLinearGradient: () => ({ addColorStop() {} }) },
    { get(target, k) { return k in target ? target[k] : () => {}; } });
  canvas.getContext = () => options.noContext ? null : context();
  document.documentElement = rootEl; document.hidden = false;
  document.querySelector = selector => selector === '.gd-stage' ? stage : null;
  document.createElement = tag => { const el = new Element(); if (tag === 'canvas') el.getContext = context; return el; };
  document.getElementById = () => ({ textContent: JSON.stringify(data) });
  const media = {};
  const observer = {};
  const sandbox = { document, console: { warn() {} }, Math, Date, Intl, JSON, Promise, Float32Array, AbortController,
    performance: { now: () => now }, devicePixelRatio: 2, innerWidth: 1200,
    localStorage: { getItem() { if (options.blockStorage) throw Error('Storage disabled'); return null; } },
    getComputedStyle: () => ({ getPropertyValue: name => ({ '--bg': '#101623', '--text': '#dde6f4', '--info': '#77aaff', '--q1': '#66bb99' }[name] || '#8899aa') }),
    matchMedia: query => { if (!media[query]) { media[query] = new Element(); media[query].matches = query.includes('hover: hover'); } return media[query]; },
    requestAnimationFrame: fn => { const id = nextId++; frames.set(id, fn); return id; },
    cancelAnimationFrame: id => frames.delete(id),
    setTimeout: (fn, delay) => { const id = nextId++; timeouts.set(id, { fn, delay }); return id; },
    clearTimeout: id => timeouts.delete(id),
    setInterval: (fn, delay) => { const id = nextId++; intervals.set(id, { fn, delay }); return id; },
    clearInterval: id => intervals.delete(id),
    fetch: async () => { requests++; if (rejectNext) throw Error('offline'); if (options.stallFetch) return new Promise(() => {}); return { ok: true, json: async () => JSON.parse(fs.readFileSync(path.join(root, 'site/world-110m.json'), 'utf8')) }; },
    ResizeObserver: class { constructor(fn) { observer.resize = fn; } observe() {} },
    IntersectionObserver: class { constructor(fn) { observer.intersection = fn; } observe() {} },
    addEventListener: win.addEventListener.bind(win) };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  for (const file of ['d3-array.min.js', 'd3-geo.min.js', 'topojson-client.min.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, 'site/vendor', file), 'utf8'), sandbox);
  }
  const seam = `window.__test = { state: function () { return { ready: ready, motion: motionOK, raf: raf,
    width: W, scale: scale, fit: fitScale, rotation: rot.slice(), flying: flying, tour: _tour.active, tier: Q }; },
    select: selectMarket, settle: _settleFlight };`;
  const source = fs.readFileSync(path.join(root, 'site/globe-deck.js'), 'utf8').replace(/\}\)\(\);\s*$/, seam + '\n})();');
  vm.runInContext(source, sandbox);
  const flush = async () => { await new Promise(resolve => setImmediate(resolve)); };
  await flush();
  return { sandbox, stage, canvas, deck, document, rootEl, tip, leg, retry, media, frames, timeouts, intervals,
    state: () => sandbox.__test?.state(), observer, requests: () => requests, flush,
    click(action) { controls.find(c => c.getAttribute('data-gd-action') === action).emit('click'); },
    succeed() { rejectNext = false; },
    frame(ms = 16.7) { now += ms; const pending = [...frames]; frames.clear(); for (const [, fn] of pending) fn(now); },
    advance(ms) { now += ms; },
    resize(width, height) { stage.rect = { width, height, left: 0, top: 0 }; observer.resize([{ contentRect: stage.rect }]); this.frame(); },
    reduce(value) { const q = media['(prefers-reduced-motion: reduce)']; q.matches = value; q.emit('change', { matches: value }); } };
}

test('shell/document visibility stops rendering and tour timers; repeated resumes own one loop', async () => {
  const s = await scene();
  assert.equal(s.deck.getAttribute('data-globe-state'), 'ready');
  assert.equal(s.frames.size, 1);
  s.click('tour'); assert.equal(s.state().tour, true);
  assert.ok([...s.timeouts.values()].some(t => t.delay === 750));
  s.document.emit('mmx:shell-visibility', { detail: { visible: false } });
  assert.equal(s.frames.size, 0); assert.equal(s.state().tour, false);
  assert.ok(![...s.timeouts.values()].some(t => t.delay === 750));
  s.document.emit('mmx:shell-visibility', { detail: { visible: true } });
  s.document.emit('mmx:shell-visibility', { detail: { visible: true } });
  assert.equal(s.frames.size, 1);
  assert.equal([...s.intervals.values()].filter(t => t.delay === 6500).length, 1);
  s.document.hidden = true; s.document.emit('visibilitychange');
  assert.equal(s.frames.size, 0); assert.equal(s.state().tour, false);
});

test('reduced motion cancels the active loop and still paints keyboard and market selection', async () => {
  const s = await scene(); s.frame(); s.reduce(true);
  assert.equal(s.state().motion, false); assert.equal(s.frames.size, 0);
  const before = s.state().rotation[0], painted = s.sandbox.__gdPerf.frames;
  s.canvas.emit('keydown', { key: 'ArrowRight' });
  assert.equal(s.state().rotation[0], before + 8);
  assert.ok(s.sandbox.__gdPerf.frames > painted);
  s.leg.emit('click'); assert.equal(s.state().flying, null);
  assert.equal(s.leg.getAttribute('aria-pressed'), 'true');
  assert.equal(s.tip.getAttribute('role'), 'dialog');
  s.sandbox.__gdSetMotion(true); assert.equal(s.state().motion, false);
});

test('container resize preserves zoom, handles zero size, and restores a paused selection without focus theft', async () => {
  const s = await scene(); s.click('motion'); s.click('zoom-in');
  const zoom = s.state().scale / s.state().fit;
  s.leg.emit('click'); const focus = s.tip.focusCount;
  const close = s.tip.querySelector('.gd-tip-close'); close.focus();
  const selectedZoom = s.state().scale / s.state().fit;
  s.resize(680, 400);
  assert.equal(s.state().width, 680); assert.ok(Math.abs(s.state().scale / s.state().fit - selectedZoom) < 1e-9);
  assert.equal(s.tip.focusCount, focus); assert.ok(zoom > 1);
  assert.equal(s.tip.querySelector('.gd-tip-close'), close);
  s.resize(0, 0); assert.equal(s.frames.size, 0);
  s.resize(600, 350); assert.equal(s.state().width, 600); assert.equal(s.state().motion, false);
});

test('fetch failure recovers through one user retry; blocked storage does not break boot', async () => {
  const s = await scene({ rejectFetch: true, blockStorage: true });
  assert.equal(s.deck.getAttribute('data-globe-state'), 'error'); assert.equal(s.requests(), 1);
  s.succeed(); s.retry.emit('click'); s.retry.emit('click'); await s.flush();
  assert.equal(s.requests(), 2); assert.equal(s.deck.getAttribute('data-globe-state'), 'ready');
  assert.equal(s.frames.size, 1);
});

test('missing canvas support leaves the dashboard fallback usable', async () => {
  const s = await scene({ noContext: true });
  assert.equal(s.deck.getAttribute('data-globe-state'), 'error');
  assert.equal(s.retry.hidden, true); assert.equal(s.requests(), 0); assert.equal(s.frames.size, 0);
});

test('a performance tier change keeps exactly one animation successor', async () => {
  const s = await scene();
  s.canvas.emit('pointerdown', { pointerType: 'mouse', clientX: 100, clientY: 100, pointerId: 1 });
  for (let i = 0; i < 55; i++) s.frame(34);
  assert.ok(s.state().tier < 2);
  assert.equal(s.frames.size, 1);
});

test('a stalled request reaches the recoverable error state within the deadline', async () => {
  const s = await scene({ stallFetch: true });
  assert.equal(s.deck.getAttribute('data-globe-state'), 'loading');
  const deadline = [...s.timeouts.values()].find(t => t.delay === 12000);
  assert.ok(deadline); deadline.fn(); await s.flush();
  assert.equal(s.deck.getAttribute('data-globe-state'), 'error');
  assert.equal(s.retry.hidden, false); assert.equal(s.frames.size, 0);
});

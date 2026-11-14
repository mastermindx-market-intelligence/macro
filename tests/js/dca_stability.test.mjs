/**
 * DCA near-zero-rate stability — executes the ACTUAL inline script from
 * templates/calculators/dollar_cost_averaging.html.j2 and the committed
 * site/tools/calculators/dollar-cost-averaging.html render.
 *
 * Two execution levels, neither a copied formula:
 *  1. whole inline <script> run under node:vm with a stub document whose
 *     DOMContentLoaded hook is captured inertly (self-check runs at load; the
 *     DOM wiring is driven by invoking the captured handler on a stub DOM);
 *  2. the template's own compute() source, brace-extracted from the same file
 *     bytes, for full-precision assertions the rounded DOM strings cannot carry.
 *
 * Pins the catastrophic-cancellation fix at i→0: Math.pow(1+i,N)-1 returns 0
 * for |i| below half an ulp of 1 (FV collapses to 0) and amplifies rounding
 * noise near it (r=1.44e-13% → ~55511 vs ~30000). The stable form is
 * expm1(N*log1p(i)); tolerance is 32*Number.EPSILON*max(1,|expected|) and the
 * tiny-gain SIGN is never asserted. The ±8% constants also pin end-of-period
 * timing: an annuity-due value (~36983) sits far outside the band.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const TEMPLATE_DIR = process.env.CALC_TEMPLATE_DIR || join(ROOT, 'templates', 'calculators');
const TPL_PATH = join(TEMPLATE_DIR, 'dollar_cost_averaging.html.j2');
const GEN_PATH =
  process.env.CALC_GENERATED_PATH || join(ROOT, 'site', 'tools', 'calculators', 'dollar-cost-averaging.html');
const TPL_SRC = readFileSync(TPL_PATH, 'utf8');
const GEN_SRC = readFileSync(GEN_PATH, 'utf8');

const SELF_CHECK_MARK = 'dollar-cost-averaging self-check';

/** Extract every inline <script> body; pick the DCA calculator block. */
function calculatorScript(source, label) {
  const blocks = [];
  let i = 0;
  while ((i = source.indexOf('<script', i)) >= 0) {
    const gt = source.indexOf('>', i);
    if (gt < 0) break;
    const end = source.indexOf('</script>', gt);
    if (end < 0) break;
    blocks.push(source.slice(gt + 1, end));
    i = end + 1;
  }
  const hits = blocks.filter((b) => b.includes(SELF_CHECK_MARK));
  assert.equal(hits.length, 1, `${label}: exactly one DCA calculator script block`);
  return hits[0];
}

const TPL_SCRIPT = calculatorScript(TPL_SRC, 'template');
const GEN_SCRIPT = calculatorScript(GEN_SRC, 'generated');

function isIdent(ch) {
  return /[A-Za-z0-9_$]/.test(ch);
}

/** Brace-match a `function name(` declaration, skipping strings/comments/regex. */
function extractFunction(source, name) {
  const needle = `function ${name}(`;
  const start = source.indexOf(needle);
  if (start < 0) throw new Error(`${name}() not found`);
  const brace = source.indexOf('{', start);
  let depth = 0;
  let i = brace;
  while (i < source.length) {
    const ch = source[i];
    if (ch === '"' || ch === "'" || ch === '`') {
      i = skipString(source, i);
      continue;
    }
    if (ch === '/' && source[i + 1] === '/') {
      i = source.indexOf('\n', i);
      if (i < 0) break;
      i += 1;
      continue;
    }
    if (ch === '/' && source[i + 1] === '*') {
      const end = source.indexOf('*/', i + 2);
      i = end < 0 ? source.length : end + 2;
      continue;
    }
    if (ch === '{') depth += 1;
    else if (ch === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(start, i + 1);
    }
    i += 1;
  }
  throw new Error('brace match failed');
}

function skipString(source, i) {
  const q = source[i];
  i += 1;
  while (i < source.length) {
    if (source[i] === '\\') {
      i += 2;
      continue;
    }
    if (source[i] === q) return i + 1;
    if (q !== '`' && source[i] === '\n') return i + 1;
    i += 1;
  }
  return i;
}

/** Run the whole inline script; the DOMContentLoaded hook is captured, not run. */
function loadScript(scriptText, label) {
  const domListeners = {};
  const consoleErrors = [];
  const documentStub = {
    listeners: domListeners,
    consoleErrors,
    documentElement: { attrs: {}, getAttribute(k) { return this.attrs[k] ?? null; } },
    body: { appendChild() {}, removeChild() {} },
    createElement() {
      return {
        className: '', textContent: '', children: [], value: '',
        appendChild(c) { this.children.push(c); },
        setAttribute() {}, getAttribute() { return null; }, select() {}, focus() {},
      };
    },
    addEventListener(type, fn) {
      (domListeners[type] ||= []).push(fn); // captured inertly; nothing fires at load
    },
  };
  const context = vm.createContext({
    document: documentStub,
    navigator: {},
    console: { error(...a) { consoleErrors.push(a.join(' ')); }, log() {}, warn() {} },
    setTimeout,
    clearTimeout,
    Math,
    Number,
    String,
    isFinite,
    Infinity,
    NaN,
    Promise,
    Error,
  });
  vm.runInContext(scriptText, context, { filename: `${label}.inline.js` });
  return { context, domListeners, consoleErrors, documentStub };
}

// ── stub DOM for the captured DOMContentLoaded wiring ─────────────────────────
function makeEl(placeholder) {
  const el = {
    value: '',
    textContent: '',
    className: '',
    hidden: false,
    placeholder: placeholder || '',
    attrs: {},
    children: [],
    listeners: {},
    classList: {
      set: new Set(),
      add(c) { this.set.add(c); },
      remove(c) { this.set.delete(c); },
      toggle(c, force) { if (force) this.set.add(c); else this.set.delete(c); },
    },
    appendChild(c) { el.children.push(c); },
    setAttribute(k, v) { el.attrs[k] = v; },
    removeAttribute(k) { delete el.attrs[k]; },
    getAttribute(k) { return k === 'placeholder' ? el.placeholder : (el.attrs[k] ?? null); },
    addEventListener(t, fn) { (el.listeners[t] ||= []).push(fn); },
    fire(t) { (el.listeners[t] || []).forEach((fn) => fn()); },
    closest() { return el; },
    querySelectorAll(sel) {
      if (sel === 'button') return el.buttons;
      return [];
    },
    buttons: [],
    rows: 4,
    scrollTop: 0,
    focus() {},
    select() {},
    scrollIntoView() {},
  };
  Object.defineProperty(el, 'clientHeight', { get() { return el.rows * 21; } });
  Object.defineProperty(el, 'scrollHeight', { get() { return el.rows * 21; } });
  return el;
}

/** Mount the captured DOMContentLoaded handler on a stub DOM; drive the UI. */
function mount(loaded) {
  const handlers = loaded.domListeners.DOMContentLoaded;
  assert.equal(handlers && handlers.length, 1, 'one DOMContentLoaded hook captured');
  const els = {};
  for (const [id, placeholder] of [
    ['contrib', '500'], ['years', '5'], ['rate', '8'],
    ['out-main'], ['out-plain'], ['out-invested'], ['out-gain'], ['out-return'], ['out-buys'],
    ['copy-result'], ['copied'], ['copy-fallback'], ['copy-fallback-text'],
  ]) els[id] = makeEl(placeholder);
  const freqWrap = makeEl('');
  freqWrap.buttons = [12, 52, 4].map((v) => {
    const b = makeEl('');
    b.dataV = String(v);
    const prev = b.getAttribute;
    b.getAttribute = (k) => (k === 'data-v' ? b.dataV : prev.call(b, k));
    return b;
  });
  freqWrap.buttons[0].classList.add('on');
  freqWrap.querySelectorAll = () => freqWrap.buttons;
  els['freq'] = freqWrap;
  const doc = loaded.documentStub;
  doc.getElementById = (id) => els[id];
  handlers[0](); // wire the UI exactly as the browser would have
  return {
    els,
    freq: freqWrap,
    clickFreq(v) {
      const b = freqWrap.buttons.find((x) => x.dataV === String(v));
      assert.ok(b, `freq button ${v}`);
      freqWrap.listeners.click.forEach((fn) => fn({ target: b }));
    },
    set(c, y, r) {
      els.contrib.value = String(c);
      els.years.value = String(y);
      els.rate.value = String(r);
      els.contrib.fire('input'); els.years.fire('input'); els.rate.fire('input');
    },
    plainText() {
      const e = els['out-plain'];
      return e.textContent + e.children.map((c) => c.textContent).join('');
    },
    biText() {
      const e = els['out-plain'];
      return e.children.map((c) => `${c.className}:${c.textContent}`).join('|');
    },
  };
}

// ── the actual compute(), extracted from the same file bytes ─────────────────
function loadCompute(source, label) {
  const limit = source.match(/\bvar\s+LIMIT\s*=\s*[^;]+;/);
  assert.ok(limit, `${label}: LIMIT declaration found`);
  const context = vm.createContext({ Math, Number, isFinite, Infinity, NaN });
  vm.runInContext(limit[0] + '\n' + extractFunction(source, 'compute'), context, { filename: `${label}.compute.js` });
  return context.compute;
}

const tplCompute = loadCompute(TPL_SRC, 'template');
const genCompute = loadCompute(GEN_SRC, 'generated');

const EPS = Number.EPSILON;
const tol = (want) => 32 * EPS * Math.max(1, Math.abs(want));
/** Template and committed page run in separate vm realms; compare by value. */
const norm = (r) => (r && typeof r === 'object' ? JSON.parse(JSON.stringify(r)) : r);
function assertClose(got, want, note) {
  assert.ok(
    Math.abs(got - want) <= tol(want),
    `${note}: got ${got} want ${want} (|Δ|=${Math.abs(got - want)} > ${tol(want)})`,
  );
}

test('template and generated pages carry the byte-identical inline calculator script', () => {
  assert.equal(TPL_SCRIPT, GEN_SCRIPT);
});

test('load-time self-check is silent on both carrier scripts', () => {
  for (const [src, label] of [[TPL_SCRIPT, 'template'], [GEN_SCRIPT, 'generated']]) {
    const loaded = loadScript(src, label);
    assert.deepEqual(loaded.consoleErrors, [], `${label}: WORKED_EXAMPLES self-check drift`);
    assert.ok(loaded.domListeners.DOMContentLoaded, `${label}: DOMContentLoaded hook captured inertly`);
  }
});

// ── the near-zero law: FV must stay ≈ c·N when i → 0 ─────────────────────────
const NEAR_ZERO = [
  ['+1e-14 % monthly', { c: 500, f: 12, yrs: 5, r: 0.00000000000001 }],
  ['-1e-14 % monthly', { c: 500, f: 12, yrs: 5, r: -0.00000000000001 }],
  ['+1.44e-13 % monthly', { c: 500, f: 12, yrs: 5, r: 0.000000000000144 }],
  ['+1e-14 % quarterly', { c: 500, f: 4, yrs: 5, r: 0.00000000000001 }],
  ['-1e-14 % quarterly', { c: 500, f: 4, yrs: 5, r: -0.00000000000001 }],
  ['+1e-14 % weekly', { c: 500, f: 52, yrs: 5, r: 0.00000000000001 }],
  ['-1e-14 % weekly', { c: 500, f: 52, yrs: 5, r: -0.00000000000001 }],
];

for (const [name, inp] of NEAR_ZERO) {
  test(`near-zero ${name}: FV ≈ c·N (${inp.c * Math.round(inp.yrs * inp.f)})`, () => {
    const got = tplCompute(inp);
    assert.equal(got.ok, true, JSON.stringify(got));
    const invested = inp.c * Math.round(inp.yrs * inp.f);
    assert.equal(got.N, Math.round(inp.yrs * inp.f));
    assert.equal(got.invested, invested);
    assertClose(got.fv, invested, 'fv');
    // gain/returnPct are fv-minus-invested cancellations: their honest bound is
    // the fv/invested scale, never tol(0). Magnitude pinned; sign never asserted.
    const gainBand = 32 * EPS * Math.max(1, Math.abs(got.fv));
    assert.ok(Math.abs(got.gain) <= gainBand, `gain=${got.gain} > ${gainBand}`);
    assert.ok(Math.abs(got.returnPct) <= 32 * EPS * 100, `returnPct=${got.returnPct}`);
    const gen = genCompute(inp);
    assert.deepEqual(norm(gen), norm(got), 'generated page parity');
  });
}

test('exact zero return stacks contributions exactly: FV === c·N', () => {
  for (const f of [4, 12, 52]) {
    const got = tplCompute({ c: 500, f, yrs: 5, r: 0 });
    assert.equal(got.ok, true);
    assert.equal(got.fv, 500 * 5 * f);
    assert.equal(got.gain, 0);
  }
});

test('rate so small that i rounds to exact 0 takes the zero branch: FV === c·N', () => {
  const got = tplCompute({ c: 500, f: 12, yrs: 5, r: 1e-330 });
  assert.equal(got.ok, true, JSON.stringify(got));
  assert.equal(got.fv, 30000);
  assert.equal(got.gain, 0);
  const gen = genCompute({ c: 500, f: 12, yrs: 5, r: 1e-330 });
  assert.deepEqual(norm(gen), norm(got));
});

test('subnormal i (r=1e-320 %) stays finite and lands on c·N, not 0 and not NaN', () => {
  const got = tplCompute({ c: 500, f: 12, yrs: 5, r: 1e-320 });
  assert.equal(got.ok, true, JSON.stringify(got));
  assert.equal(Number.isFinite(got.fv), true, `fv=${got.fv}`);
  assert.ok(got.fv > 0, `fv=${got.fv}`);
  // subnormal products carry ~2^-11 relative granularity; a correct stable form
  // stays within 1e-9 relative of c·N, while the pow form collapses to 0.
  assert.ok(Math.abs(got.fv - 30000) <= 30000 * 1e-9, `fv=${got.fv}`);
  const gen = genCompute({ c: 500, f: 12, yrs: 5, r: 1e-320 });
  assert.deepEqual(norm(gen), norm(got));
});

test('N=1 at a near-zero rate returns exactly one contribution', () => {
  const got = tplCompute({ c: 500, f: 12, yrs: 1 / 12, r: 0.00000000000001 });
  assert.equal(got.ok, true, JSON.stringify(got));
  assert.equal(got.N, 1);
  assertClose(got.fv, 500, 'fv');
  const gen = genCompute({ c: 500, f: 12, yrs: 1 / 12, r: 0.00000000000001 });
  assert.deepEqual(norm(gen), norm(got));
});

// ── ordinary rates: pinned constants (also pin end-of-period timing) ─────────
test('ordinary +8% monthly 500×5y lands on 36738.4281226208…', () => {
  const got = tplCompute({ c: 500, f: 12, yrs: 5, r: 8 });
  assert.equal(got.ok, true);
  assert.equal(got.N, 60);
  assert.equal(got.invested, 30000);
  assertClose(got.fv, 36738.428122620825, 'fv');
  assertClose(got.gain, 6738.428122620825, 'gain');
  const gen = genCompute({ c: 500, f: 12, yrs: 5, r: 8 });
  assert.deepEqual(norm(gen), norm(got));
});

test('ordinary -8% monthly 500×5y lands on 24793.2829015438…', () => {
  const got = tplCompute({ c: 500, f: 12, yrs: 5, r: -8 });
  assert.equal(got.ok, true);
  assert.equal(got.N, 60);
  assertClose(got.fv, 24793.282901543867, 'fv');
  assertClose(got.gain, -5206.717098456133, 'gain');
  const gen = genCompute({ c: 500, f: 12, yrs: 5, r: -8 });
  assert.deepEqual(norm(gen), norm(got));
});

test('N rounding follows Math.round(yrs·f)', () => {
  assert.equal(tplCompute({ c: 500, f: 12, yrs: 0.4, r: 8 }).N, 5); // 4.8 → 5
  assert.equal(tplCompute({ c: 500, f: 4, yrs: 2.6, r: 8 }).N, 10); // 10.4 → 10
  assert.equal(tplCompute({ c: 500, f: 52, yrs: 0.1, r: 8 }).N, 5); // 5.2 → 5
});

// ── preserved boundaries: i ≤ -1 fallback, sign acceptance, overflow ─────────
test('i = -1 exactly (r = -100·f) falls back to the single contribution c', () => {
  const got = tplCompute({ c: 500, f: 12, yrs: 5, r: -1200 });
  assert.equal(got.ok, true, JSON.stringify(got));
  assert.equal(got.fv, 500);
  assert.equal(got.gain, -29500);
  const gen = genCompute({ c: 500, f: 12, yrs: 5, r: -1200 });
  assert.deepEqual(norm(gen), norm(got));
});

test('i < -1 keeps the pow fallback (total-loss regime stays finite)', () => {
  const got = tplCompute({ c: 500, f: 12, yrs: 5, r: -1300 });
  assert.equal(got.ok, true, JSON.stringify(got));
  assert.ok(Number.isFinite(got.fv) && got.fv > 0 && got.fv < 500, `fv=${got.fv}`);
  assertClose(got.fv, 500 / 1.0833333333333333, 'fv');
  const gen = genCompute({ c: 500, f: 12, yrs: 5, r: -1300 });
  assert.deepEqual(norm(gen), norm(got));
});

test('deep negative underflow stays finite and matches the committed page', () => {
  const inp = { c: 500, f: 4, yrs: 5000, r: -99.9999999 };
  const got = tplCompute(inp);
  assert.equal(got.ok, true, JSON.stringify(got));
  assert.ok(Number.isFinite(got.fv) && got.fv > 0, `fv=${got.fv}`);
  const gen = genCompute(inp);
  assert.deepEqual(norm(gen), norm(got));
});

test('overflow through the stable form is still withheld, bilingually', () => {
  const got = tplCompute({ c: 500, f: 12, yrs: 50, r: 1e9 });
  assert.equal(got.ok, false, JSON.stringify(got));
  assert.equal(got.overflow, true);
  assert.equal(typeof got.msg.en, 'string');
  assert.equal(typeof got.msg.zh, 'string');
  assert.ok(got.msg.en.length > 0 && got.msg.zh.length > 0);
  const gen = genCompute({ c: 500, f: 12, yrs: 50, r: 1e9 });
  assert.deepEqual(norm(gen), norm(got));
});

test('negative ordinary rates are accepted, not rejected', () => {
  for (const r of [-0.5, -2.75, -8, -50, -99]) {
    const got = tplCompute({ c: 500, f: 12, yrs: 5, r });
    assert.equal(got.ok, true, `r=${r}: ${JSON.stringify(got)}`);
    assert.equal(got.N, 60);
  }
});

// ── broad candidate↔source parity sweep ──────────────────────────────────────
test('template and committed page agree across frequencies × rates × years', () => {
  for (const f of [4, 12, 52]) {
    for (const r of [0, 0.00000000000001, -0.00000000000001, 0.000000000000144, 8, -8, 2.75, -0.5]) {
      for (const yrs of [5, 1 / 12, 0.4]) {
        const a = tplCompute({ c: 500, f, yrs, r });
        const b = genCompute({ c: 500, f, yrs, r });
        assert.deepEqual(norm(b), norm(a), `f=${f} r=${r} yrs=${yrs}`);
        if (a.ok) {
          assert.equal(Number.isFinite(a.fv), true, `f=${f} r=${r} yrs=${yrs}`);
          assert.equal(Number.isFinite(a.gain), true);
          assert.equal(a.invested, 500 * Math.round(yrs * f));
        }
      }
    }
  }
});

// ── whole-script UI wiring: frequencies, validation, recovery, copy ──────────
test('UI renders every cadence and matches compute: f=4/12/52', () => {
  for (const [src, label] of [[TPL_SCRIPT, 'template'], [GEN_SCRIPT, 'generated']]) {
    const ui = mount(loadScript(src, label));
    ui.set('500', '5', '8');
    const want = {
      4: { buys: '20', invested: '$10,000.00', main: '$12,149' },
      12: { buys: '60', invested: '$30,000.00', main: '$36,738' },
      52: { buys: '260', invested: '$130,000.00', main: '$159,694' },
    };
    for (const f of [4, 12, 52]) {
      ui.clickFreq(f);
      const res = tplCompute({ c: 500, f, yrs: 5, r: 8 });
      assert.equal(res.ok, true);
      assert.equal(ui.els['out-main'].textContent, '$' + Math.round(res.fv).toLocaleString('en-US'), `${label} f=${f} main`);
      assert.equal(ui.els['out-main'].textContent, want[f].main, `${label} f=${f} pinned main`);
      assert.equal(ui.els['out-buys'].textContent, want[f].buys, `${label} f=${f} buys`);
      assert.equal(ui.els['out-invested'].textContent, want[f].invested, `${label} f=${f} invested`);
      assert.equal(ui.els['out-gain'].className, 'pos', `${label} f=${f} gain class`);
      assert.ok(ui.plainText().includes('projects to'), `${label} f=${f} plain sentence`);
    }
  }
});

test('UI end-of-period timing: monthly 8% shows $36,738, invested $30,000, gain $6,738', () => {
  const ui = mount(loadScript(TPL_SCRIPT, 'template'));
  ui.set('500', '5', '8');
  assert.equal(ui.els['out-main'].textContent, '$36,738');
  assert.equal(ui.els['out-invested'].textContent, '$30,000.00');
  assert.equal(ui.els['out-gain'].textContent, '$6,738.43');
  assert.ok(ui.els['out-return'].textContent.startsWith('22'));
  assert.equal(ui.els['out-buys'].textContent, '60');
});

test('UI near-zero rates project the contributions, not zero', () => {
  const ui = mount(loadScript(TPL_SCRIPT, 'template'));
  ui.set('500', '5', '0.00000000000001');
  assert.equal(ui.els['out-main'].textContent, '$30,000');
  assert.equal(ui.els['out-invested'].textContent, '$30,000.00');
  ui.clickFreq(4);
  assert.equal(ui.els['out-main'].textContent, '$10,000');
  ui.clickFreq(52);
  assert.equal(ui.els['out-main'].textContent, '$130,000');
  ui.clickFreq(12);
  ui.set('500', '5', '-0.00000000000001');
  assert.equal(ui.els['out-main'].textContent, '$30,000');
});

test('UI rejects malformed input bilingually, marks the field, and recovers', () => {
  const ui = mount(loadScript(TPL_SCRIPT, 'template'));
  ui.set('500', '5', '8');
  assert.equal(ui.els['out-main'].textContent, '$36,738');
  ui.set('500', '5', '12abc');
  assert.equal(ui.els['out-main'].textContent, '—');
  assert.equal(ui.els['rate'].getAttribute('aria-invalid'), 'true');
  assert.ok(ui.els['out-plain'].className.includes('warn'));
  const bi = ui.biText().split('|');
  assert.ok(bi.some((s) => s.startsWith('l-en:') && s.includes('enter a number')), bi.join(' '));
  assert.ok(bi.some((s) => s.startsWith('l-zh:') && s.includes('请输入数字')), bi.join(' '));
  ui.set('500', '5', '8');
  assert.equal(ui.els['out-main'].textContent, '$36,738');
  assert.equal(ui.els['rate'].getAttribute('aria-invalid'), null);
});

test('blank and invalid states surface bilingual compute messages', () => {
  const ui = mount(loadScript(TPL_SCRIPT, 'template'));
  ui.set('', '5', '8');
  const en = ui.plainText();
  assert.ok(en.includes('Enter a contribution above zero.'), en);
  ui.set('500', '0.01', '8');
  assert.ok(ui.plainText().includes('too short'), ui.plainText());
});

test('copy succeeds through the clipboard path with inputs and results', async () => {
  const loaded = loadScript(TPL_SCRIPT, 'template');
  const written = [];
  loaded.context.navigator.clipboard = { writeText: (t) => { written.push(t); return Promise.resolve(); } };
  const ui = mount(loaded);
  ui.set('500', '5', '8');
  ui.els['copy-result'].fire('click');
  await new Promise((r) => setTimeout(r, 10));
  assert.equal(ui.els['copied'].classList.set.has('show'), true, 'copied badge shown');
  assert.equal(written.length, 1);
  const text = written[0];
  assert.ok(text.includes('Mastermind dollar-cost averaging calculator (hypothetical scenario)'), text);
  assert.ok(text.includes('$36,738') && text.includes('$30,000') && text.includes('$6,738'), text);
  assert.ok(text.includes('60'), text);
});

test('copy falls back to the selectable textarea when the clipboard refuses', async () => {
  const loaded = loadScript(TPL_SCRIPT, 'template');
  loaded.context.navigator.clipboard = { writeText: () => Promise.reject(new Error('denied')) };
  loaded.documentStub.execCommand = () => false;
  const ui = mount(loaded);
  ui.set('500', '5', '8');
  ui.els['copy-result'].fire('click');
  await new Promise((r) => setTimeout(r, 10));
  assert.equal(ui.els['copied'].classList.set.has('show'), false, 'no copied badge');
  assert.equal(ui.els['copy-fallback'].hidden, false, 'fallback revealed');
  assert.ok(ui.els['copy-fallback-text'].value.includes('$36,738'), ui.els['copy-fallback-text'].value);
});

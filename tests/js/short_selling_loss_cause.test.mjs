// Executes the real inline calculator script from both checked-in artifacts
// (Jinja template + committed site page). Source-level regression for the
// net-loss cause sentence: borrow fees can produce a net loss while the stock
// fell or never moved, so the loss narrative must branch on gross direction
// instead of claiming a rise unconditionally. No native clipboard or browser
// proof — those are separate acceptance claims.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const SOURCES = [
  'templates/calculators/short_selling.html.j2',
  'site/tools/calculators/short-selling.html',
];

// Unique final-render adapter seam inside the DOMContentLoaded handler.
const ANCHOR = '    render();\n  });';

// The cause branch under test, and the pre-fix single-cause form used only as
// a negative control.
const FIXED_CAUSE_BLOCK =
  '        var cause = res.gross < 0 ? "the stock rose against the position"\n' +
  '          : (res.gross > 0 ? "borrow fees exceeded the gain from the stock decline"\n' +
  '            : "borrow fees caused the loss while the stock price was unchanged");\n' +
  '        plain = "This short lost " + money(res.net) + " — " + cause + ", a " +';
const PRE_FIX_LINE =
  '        plain = "This short lost " + money(res.net) + " — the stock rose against the position, a " +';

// entry $50, 100 shares throughout (set by input()).
const FALLING_FEE_LOSS = { cover: 49, bfee: 50, days: 30 };  // gross +$100.00, borrow $205.48, net -$105.48 / -2.11%
const FLAT_FEE_LOSS = { cover: 50, bfee: 5, days: 30 };      // gross  $0.00, borrow  $20.55, net  -$20.55 / -0.41%
const RISING_FEE_LOSS = { cover: 51, bfee: 5, days: 30 };    // gross -$100.00, borrow $20.55, net -$120.55 / -2.41%
const RISING_NO_FEE = { cover: 60 };                         // net -$1,000.00 / -20.0%
const FALLING_FEE_PROFIT = { cover: 40, bfee: 5, days: 30 }; // net +$979.45
const FEE_BREAKEVEN = { cover: 49.5, bfee: 365, days: 1 };   // gross +$50.00, borrow $50.00, net $0.00

function calculatorScript(path, transform = (source) => source) {
  const source = readFileSync(
    new URL(`../../${path}`, import.meta.url), 'utf8',
  ).replace(/\r\n/g, '\n');

  const scripts = [...source.matchAll(
    /<script\b[^>]*>([\s\S]*?)<\/script>/gi,
  )].map((match) => match[1]).filter((script) =>
    script.includes('function compute(inp)') &&
    script.includes('function copyLine()'),
  );
  assert.equal(scripts.length, 1, `${path}: unique calculator script`);

  return transform(scripts[0]);
}

function loadClient(path, transform) {
  const raw = calculatorScript(path, transform);

  // Fail closed if the source structure changes. Only expose references; do
  // not replace compute, render, copyLine, or their lexical dependencies.
  assert.equal(
    raw.split(ANCHOR).length, 2,
    `${path}: unique final-render adapter seam`,
  );
  const instrumented = raw.replace(ANCHOR, `
    globalThis.__shortSellingTest = {
      compute: compute,
      copyLine: copyLine,
      current: function(){ return last; }
    };
${ANCHOR}`);

  const ids = [
    'entry', 'cover', 'shares', 'bfee', 'days',
    'out-main', 'out-plain', 'out-gross', 'out-borrow', 'out-ret',
    'copy-result', 'copied',
  ];
  const nodes = Object.fromEntries(ids.map((id) => [id, {
    value: '',
    textContent: '',
    className: '',
    classList: { add() {}, remove() {} },
    listeners: new Map(),
    addEventListener(type, fn) {
      assert.equal(this.listeners.has(type), false, `${id}: duplicate ${type}`);
      this.listeners.set(type, fn);
    },
  }]));

  let ready;
  const errors = [];
  const context = vm.createContext({
    navigator: {
      clipboard: { writeText() { return Promise.resolve(); } },
    },
    setTimeout(fn) { return fn(); },
    document: {
      getElementById(id) {
        assert.ok(nodes[id], `unexpected element ${id}`);
        return nodes[id];
      },
      addEventListener(type, fn) {
        assert.equal(type, 'DOMContentLoaded');
        assert.equal(ready, undefined);
        ready = fn;
      },
      createElement() { throw new Error('legacy fallback must not be exercised'); },
      body: {
        appendChild() { throw new Error('unexpected appendChild'); },
        removeChild() { throw new Error('unexpected removeChild'); },
      },
    },
    console: { error: (...args) => errors.push(args.join(' ')) },
  });
  new vm.Script(instrumented, { filename: path })
    .runInContext(context, { timeout: 1000 });
  assert.equal(typeof ready, 'function');
  ready();

  const api = context.__shortSellingTest;
  assert.equal(typeof api.compute, 'function');
  assert.equal(typeof api.copyLine, 'function');
  for (const id of ['entry', 'cover', 'shares', 'bfee', 'days']) {
    assert.equal(typeof nodes[id].listeners.get('input'), 'function');
  }
  assert.equal(typeof nodes['copy-result'].listeners.get('click'), 'function');

  return {
    nodes,
    errors,
    copy: () => api.copyLine(),
    input({ cover, bfee = '', days = '' }) {
      // Run the real registered input callback, which calls the real render()
      // and compute(), including the real assignment to last on failure.
      nodes.entry.value = '50';
      nodes.shares.value = '100';
      nodes.cover.value = String(cover);
      nodes.bfee.value = bfee === '' ? '' : String(bfee);
      nodes.days.value = days === '' ? '' : String(days);
      nodes.cover.listeners.get('input')();
      return api.current();
    },
  };
}

for (const path of SOURCES) {
  test(`${path}: fee-driven loss on a falling stock names the fee, not a rise`, () => {
    const client = loadClient(path);
    const res = client.input(FALLING_FEE_LOSS);
    assert.equal(res.ok, true);
    assert.deepEqual(client.errors, [], `${path}: embedded worked examples`);
    assert.equal(client.nodes['out-main'].textContent, '-$105.48');
    assert.equal(client.nodes['out-gross'].textContent, '$100.00');
    assert.equal(client.nodes['out-borrow'].textContent, '$205.48');
    const plain = client.nodes['out-plain'].textContent;
    assert.ok(plain.includes('This short lost -$105.48'));
    assert.ok(plain.includes('borrow fees exceeded the gain from the stock decline'),
      `${path}: fee-dominated loss must name the fee cause`);
    assert.ok(!plain.includes('rose'),
      `${path}: the stock fell — a rising-stock narrative is false`);
    assert.ok(plain.includes('including a $205.48 borrow fee.'));
    assert.equal(client.nodes['out-plain'].className, 'co-plain warn');
    assert.equal(client.copy(),
      'Short selling loss: -$105.48 (-2.11% on notional) · gross $100.00 · borrow $205.48 — mastermind-x.com');
  });

  test(`${path}: fee-driven loss on an unchanged stock names the unchanged price`, () => {
    const client = loadClient(path);
    const res = client.input(FLAT_FEE_LOSS);
    assert.equal(res.ok, true);
    assert.equal(client.nodes['out-main'].textContent, '-$20.55');
    assert.equal(client.nodes['out-gross'].textContent, '$0.00');
    const plain = client.nodes['out-plain'].textContent;
    assert.ok(plain.includes('borrow fees caused the loss while the stock price was unchanged'),
      `${path}: flat-price fee loss must name the unchanged price`);
    assert.ok(!plain.includes('rose'),
      `${path}: the stock never moved — a rising-stock narrative is false`);
    assert.equal(client.copy(),
      'Short selling loss: -$20.55 (-0.41% on notional) · gross $0.00 · borrow $20.55 — mastermind-x.com');
  });

  test(`${path}: rising-stock losses keep the rising narrative, with and without fees`, () => {
    for (const scenario of [RISING_NO_FEE, RISING_FEE_LOSS]) {
      const client = loadClient(path);
      const res = client.input(scenario);
      assert.equal(res.ok, true);
      const plain = client.nodes['out-plain'].textContent;
      assert.ok(plain.includes('the stock rose against the position'),
        `${path}: a genuine rise keeps its cause`);
      assert.ok(!plain.includes('borrow fees exceeded'));
      assert.ok(!plain.includes('price was unchanged'));
    }
    const client = loadClient(path);
    client.input(RISING_FEE_LOSS);
    assert.equal(client.nodes['out-main'].textContent, '-$120.55');
    assert.equal(client.copy(),
      'Short selling loss: -$120.55 (-2.41% on notional) · gross -$100.00 · borrow $20.55 — mastermind-x.com');
  });

  test(`${path}: profits and breakevens keep their existing narratives`, () => {
    const profit = loadClient(path);
    profit.input(FALLING_FEE_PROFIT);
    assert.equal(profit.nodes['out-main'].textContent, '$979.45');
    assert.ok(profit.nodes['out-plain'].textContent.includes('This short made $979.45'));
    assert.equal(profit.nodes['out-plain'].className, 'co-plain');
    assert.ok(profit.copy().startsWith('Short selling profit: $979.45'));

    const noFee = loadClient(path);
    noFee.input({ cover: 50 });
    assert.equal(noFee.nodes['out-main'].textContent, '$0.00');
    assert.ok(noFee.nodes['out-plain'].textContent.includes('broke even'));
    assert.equal(noFee.nodes['out-borrow'].textContent, '—');
    assert.ok(noFee.copy().startsWith('Short selling profit: $0.00'));

    const feeBreak = loadClient(path);
    feeBreak.input(FEE_BREAKEVEN);
    assert.equal(feeBreak.nodes['out-main'].textContent, '$0.00');
    assert.equal(feeBreak.nodes['out-borrow'].textContent, '$50.00');
    assert.ok(feeBreak.nodes['out-plain'].textContent.includes('broke even'));
  });

  test(`${path}: loss-to-profit transition clears the warn state`, () => {
    const client = loadClient(path);
    client.input(FLAT_FEE_LOSS);
    assert.equal(client.nodes['out-plain'].className, 'co-plain warn');
    client.input(FALLING_FEE_PROFIT);
    const plain = client.nodes['out-plain'].textContent;
    assert.ok(plain.includes('This short made'));
    assert.ok(!plain.includes('stock rose'));
    assert.equal(client.nodes['out-plain'].className, 'co-plain');
  });

  test(`${path}: invalid input clears outputs and recovers`, () => {
    const client = loadClient(path);
    client.input(FALLING_FEE_PROFIT);
    client.nodes.entry.value = '';
    client.nodes.entry.listeners.get('input')();
    assert.equal(client.nodes['out-main'].textContent, '—');
    assert.equal(client.nodes['out-plain'].textContent,
      'Enter the price you shorted at.');
    assert.equal(client.copy(), '');
    client.input(FALLING_FEE_PROFIT);
    assert.equal(client.nodes['out-main'].textContent, '$979.45');
    assert.ok(client.nodes['out-plain'].textContent.includes('This short made'));
  });

  test(`${path}: negative control — the pre-fix narrative misattributes a flat-price fee loss`, () => {
    const client = loadClient(path, (source) => {
      assert.ok(source.includes(FIXED_CAUSE_BLOCK), `${path}: cause branch under test is present`);
      return source.replace(FIXED_CAUSE_BLOCK, PRE_FIX_LINE);
    });
    client.input(FLAT_FEE_LOSS);
    const plain = client.nodes['out-plain'].textContent;
    assert.ok(plain.includes('the stock rose against the position'),
      `${path}: the pre-fix defect must be observable through this harness`);
  });
}

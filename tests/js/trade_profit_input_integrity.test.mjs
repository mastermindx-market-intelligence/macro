import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import vm from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const files = [
  'templates/calculators/trade_profit.html.j2',
  'site/tools/calculators/trade-profit.html',
];
const outputs = ['out-main', 'out-ret', 'out-ann', 'out-cost', 'out-days'];
const ordinary = { entry: '50', exit: '55', qty: '100', fees: '2' };

function controller(file) {
  const source = fs.readFileSync(path.join(root, file), 'utf8');
  const scripts = [...source.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)];
  const found = scripts.find((match) => match[1].includes('function compute(inp)') && match[1].includes('Trade P/L:'));
  assert.ok(found, `Trade Profit controller in ${file}`);
  return found[1];
}

function application(file, input = ordinary) {
  const nodes = new Map();
  const writes = [];
  const errors = [];
  function node(id) {
    if (!nodes.has(id)) {
      const classes = new Set();
      nodes.set(id, {
        value: '', textContent: '', className: '', dataset: {}, handlers: {},
        classList: { add: (name) => classes.add(name), remove: (name) => classes.delete(name) },
        addEventListener(event, handler) { this.handlers[event] = handler; },
        querySelectorAll() { return []; },
      });
    }
    return nodes.get(id);
  }
  let ready;
  const document = {
    getElementById: node,
    addEventListener(event, handler) { if (event === 'DOMContentLoaded') ready = handler; },
    body: { appendChild() {}, removeChild() {} },
    createElement() { return { value: '', select() {} }; },
    execCommand() { throw new Error('Unexpected fallback clipboard'); },
  };
  for (const [key, value] of Object.entries(input)) {
    if (key !== 'direction') node(key).value = value;
  }
  vm.runInNewContext(controller(file), {
    document,
    navigator: { clipboard: { writeText(text) { writes.push(text); return Promise.resolve(); } } },
    console: { error(...args) { errors.push(args); } },
    setTimeout() { return 1; },
  }, { filename: file, timeout: 1000 });
  assert.equal(typeof ready, 'function');
  ready();
  if (input.direction === 'short') {
    const button = { dataset: { v: 'short' }, classList: { add() {} } };
    node('direction-seg').handlers.click({ target: { closest() { return button; } } });
  }
  assert.deepEqual(errors, [], 'built-in worked examples remain valid');
  return {
    node, writes,
    input(key, value) { node(key).value = value; node(key).handlers.input(); },
    copy() {
      const count = writes.length;
      node('copy-result').handlers.click();
      return writes.slice(count);
    },
  };
}

function withheld(app) {
  for (const id of outputs) assert.equal(app.node(id).textContent, '—', id);
  assert.equal(app.node('out-main').className, '', 'invalid output has no profit/loss class');
  assert.deepEqual(app.copy(), [], 'invalid result cannot create a new clipboard write');
}

test('template and committed page execute byte-identical controllers', () => {
  assert.equal(controller(files[0]), controller(files[1]));
});

for (const file of files) {
  test(`${file}: ordinary long, short, blank fee and annualization`, () => {
    const app = application(file);
    assert.equal(app.node('out-main').textContent, '$498');
    assert.equal(app.node('out-ret').textContent, '+9.96%');
    assert.match(app.copy()[0], /Trade P\/L: \$498 \(\+9\.96% return, long\)/);
    const short = application(file, { entry: '200', exit: '210', qty: '10', fees: '0', direction: 'short' });
    assert.equal(short.node('out-main').textContent, '-$100');
    assert.equal(short.node('out-ret').textContent, '-5.00%');
    for (const fees of ['', '   ']) assert.equal(application(file, { ...ordinary, fees }).node('out-main').textContent, '$500');
    app.input('date-open', '2025-01-01');
    app.input('date-close', '2026-01-01');
    assert.equal(app.node('out-days').textContent, '365');
    assert.match(app.node('out-ann').textContent, /^\+10\.0%/);
    assert.match(app.copy()[0], /365d · annualized \+10\.0%/);
  });

  test(`${file}: declared whole-token decimal, grouping and exponent grammar`, () => {
    for (const input of [
      { entry: '5e1', exit: '+5.5e1', qty: '1e2', fees: '2.' },
      { entry: ' 50 ', exit: '55', qty: '100', fees: '2' },
    ]) assert.equal(application(file, input).node('out-main').textContent, '$498');
    assert.equal(application(file, { entry: '1,000', exit: '1,100', qty: '1.5', fees: '.5' }).node('out-main').textContent, '$149.5');
    for (const [field, values] of [
      ['fees', ['banana', '1e309', '20oops', '-2', '1,00', '0x10', 'Infinity', 'NaN']],
      ['entry', ['50oops', '', '0', '1 00', '1,2,3', '1e-999', '1'.repeat(129)]],
      ['exit', ['', '0', '55oops']],
      ['qty', ['', '0', '-1', '100units']],
    ]) for (const value of values) withheld(application(file, { ...ordinary, [field]: value }));
  });

  test(`${file}: required-output overflow and nonzero underflow withhold the result`, () => {
    for (const input of [
      { entry: '1e308', exit: '1e308', qty: '10', fees: '0' },
      { entry: '1', exit: '1e308', qty: '10', fees: '0' },
      { entry: '1', exit: '1e307', qty: '1', fees: '0' },
      { entry: '1e-300', exit: '2e-300', qty: '1e-100', fees: '0' },
      { entry: '1', exit: '1.' + '0'.repeat(29) + '1', qty: '1e-300', fees: '0' },
      { entry: '1e300', exit: '1e300', qty: '1', fees: '1e-100' },
    ]) withheld(application(file, input));
    const large = application(file, { entry: '1e200', exit: '2e200', qty: '1e100', fees: '0' });
    assert.equal(large.node('out-ret').textContent, '+100.00%', 'representable percentage avoids intermediate overflow');
    assert.equal(large.copy().length, 1);
    const small = application(file, { entry: '1e-300', exit: '2e-300', qty: '1', fees: '0' });
    assert.equal(small.node('out-ret').textContent, '+100.00%');
  });

  test(`${file}: exact decimal breakeven retains nearby real loss/gain directions`, () => {
    for (const input of [
      { entry: '0.1', exit: '0.3', qty: '10', fees: '2' },
      { entry: '0.3', exit: '0.1', qty: '10', fees: '2', direction: 'short' },
      { entry: '1.005', exit: '1.015', qty: '100', fees: '1' },
    ]) {
      const app = application(file, input);
      assert.equal(app.node('out-main').textContent, '$0');
      assert.equal(app.node('out-ret').textContent, '+0.00%');
      assert.equal(app.node('out-main').className, 'pos');
      assert.doesNotMatch(app.node('out-plain').textContent, /lost/);
      assert.doesNotMatch(app.copy()[0], /-\$0|-0\.00%/);
    }
    for (const [fees, sign, word] of [['2.00000001', 'neg', 'lost'], ['1.99999999', 'pos', 'made']]) {
      const app = application(file, { entry: '0.1', exit: '0.3', qty: '10', fees });
      assert.equal(app.node('out-main').className, sign);
      assert.ok(app.node('out-plain').textContent.includes(word));
      assert.equal(app.copy().length, 1);
    }
  });

  test(`${file}: invalidation cannot export or retain a current result; valid recovery is fresh`, () => {
    const app = application(file);
    assert.equal(app.copy().length, 1);
    for (const invalid of ['banana', '20oops', '1e309']) {
      app.input('fees', invalid);
      withheld(app);
      assert.equal(app.writes.length, 1, 'the earlier valid clipboard write remains historical');
    }
    app.input('fees', '3');
    assert.equal(app.node('out-main').textContent, '$497');
    assert.match(app.copy()[0], /Trade P\/L: \$497/);
    assert.equal(app.writes.length, 2);
  });

  test(`${file}: optional annualization does not erase a finite primary loss`, () => {
    const app = application(file, { entry: '1', exit: '3', qty: '1', fees: '0', direction: 'short', 'date-open': '2025-01-01', 'date-close': '2026-01-01' });
    assert.equal(app.node('out-main').textContent, '-$2');
    assert.equal(app.node('out-ret').textContent, '-200.00%');
    assert.equal(app.node('out-ann').textContent, '—');
    assert.equal(app.node('out-days').textContent, '365');
    assert.match(app.node('out-plain').textContent, /can't be annualized/);
    assert.doesNotMatch(app.copy()[0], /annualized/);
  });
}

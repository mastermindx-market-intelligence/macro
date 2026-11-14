// Executes the real inline calculator script from both checked-in artifacts.
// Source-level regression for the unavailable-annualized-value path; no native
// clipboard or browser proof.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const SOURCES = [
  'templates/calculators/covered_call.html.j2',
  'site/tools/calculators/covered-call.html',
];

// Unique final-render adapter seam inside the DOMContentLoaded handler.
const ANCHOR = '    render();\n  });';

// The guard under test, and the pre-fix form used only as a negative control.
const FIXED_GUARD = 'res.hasDays && res.annualizedIfCalled !== null ?';
const PRE_FIX_GUARD = 'res.hasDays ?';

const ORDINARY = { c: 100, K: 105, prem: 3, d: 30 };
// 10 / 100 / 2 / 1 day: the if-called return is +920% and the annualization
// overflows to Infinity, which compute() withholds as null.
const OVERFLOW = { c: 10, K: 100, prem: 2, d: 1 };

const ORDINARY_COPY =
  /^Covered call: static 3\.00% · if called 8\.00% · break-even \$97\.00 · ~155\.0\d% annualized \(hypothetical\) — mastermind-x\.com$/;
const OVERFLOW_COPY =
  'Covered call: static 20.00% · if called 920.00% · break-even $8.00 — mastermind-x.com';

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
    globalThis.__coveredCallTest = {
      compute: compute,
      copyLine: copyLine,
      current: function(){ return last; }
    };
${ANCHOR}`);

  const ids = [
    'basis', 'strike', 'prem', 'days',
    'out-main', 'out-plain', 'out-static', 'out-breakeven',
    'out-protect', 'out-annual', 'copy-result', 'copied',
  ];
  const nodes = Object.fromEntries(ids.map((id) => [id, {
    value: '',
    textContent: '',
    className: '',
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

  const api = context.__coveredCallTest;
  assert.equal(typeof api.compute, 'function');
  assert.equal(typeof api.copyLine, 'function');
  for (const id of ['basis', 'strike', 'prem', 'days']) {
    assert.equal(typeof nodes[id].listeners.get('input'), 'function');
  }

  return {
    nodes,
    errors,
    copy: () => api.copyLine(),
    input({ c, K, prem, d }) {
      // Run the real registered input callback, which calls the real render()
      // and compute(), including the real assignment to last on failure.
      nodes.basis.value = c == null ? '' : String(c);
      nodes.strike.value = K == null ? '' : String(K);
      nodes.prem.value = prem == null ? '' : String(prem);
      nodes.days.value = d == null ? '' : String(d);
      nodes.days.listeners.get('input')();
      return api.current();
    },
  };
}

for (const path of SOURCES) {
  test(`${path}: ordinary trade renders and copies the annualized value`, () => {
    const client = loadClient(path);
    const res = client.input(ORDINARY);
    assert.equal(res.ok, true);
    assert.deepEqual(client.errors, [], `${path}: embedded worked examples`);
    assert.equal(client.nodes['out-main'].textContent, '8.00%');
    assert.equal(client.nodes['out-static'].textContent, '3.00%');
    assert.equal(client.nodes['out-breakeven'].textContent, '$97.00');
    assert.equal(client.nodes['out-protect'].textContent, '3.00%');
    assert.match(client.nodes['out-annual'].textContent, /^155\.0\d%$/);
    assert.match(client.nodes['out-plain'].textContent,
      /Annualized, the if-called return is 155\.0\d%/);
    assert.match(client.copy(), ORDINARY_COPY);
  });

  test(`${path}: overflow to an unavailable value never throws and refreshes every field`, () => {
    const client = loadClient(path);
    client.input(ORDINARY);
    const res = client.input(OVERFLOW);
    assert.equal(res.ok, true);
    assert.equal(res.annualizedIfCalled, null, 'overflow must be withheld');
    assert.equal(client.nodes['out-main'].textContent, '920.00%');
    assert.equal(client.nodes['out-static'].textContent, '20.00%');
    assert.equal(client.nodes['out-breakeven'].textContent, '$8.00');
    assert.equal(client.nodes['out-annual'].textContent, '—');

    const plain = client.nodes['out-plain'].textContent;
    assert.ok(plain.includes('920.00%'));
    assert.ok(plain.includes('$8.00'));
    assert.ok(!plain.includes('155.0'), 'stale annualization in the narrative');
    assert.ok(!plain.includes('$97'), 'stale break-even in the narrative');
    assert.ok(!plain.includes('Annualized'), 'no annualized sentence when the value is unavailable');
  });

  test(`${path}: blank and zero days withhold annualization without throwing`, () => {
    for (const d of [0, null]) {
      const client = loadClient(path);
      const res = client.input({ ...ORDINARY, d });
      assert.equal(res.ok, true);
      assert.equal(res.annualizedIfCalled, null);
      assert.equal(client.nodes['out-main'].textContent, '8.00%');
      assert.equal(client.nodes['out-annual'].textContent, '—');
      assert.ok(!client.nodes['out-plain'].textContent.includes('Annualized'));
      assert.ok(!client.copy().includes('annualized'));
    }
  });

  test(`${path}: the copied line carries exactly the displayed values`, () => {
    const client = loadClient(path);
    client.input(ORDINARY);
    assert.match(client.copy(), ORDINARY_COPY);

    client.input(OVERFLOW);
    const line = client.copy();
    assert.equal(line, OVERFLOW_COPY);
    assert.equal(line.includes('annualized'), false);
    assert.ok(line.includes(client.nodes['out-static'].textContent));
    assert.ok(line.includes(client.nodes['out-main'].textContent));
    assert.ok(line.includes(client.nodes['out-breakeven'].textContent));
  });

  test(`${path}: negative control — the pre-fix renderer throws on the same input`, () => {
    const client = loadClient(path, (source) => {
      assert.ok(source.includes(FIXED_GUARD), `${path}: guard under test is present`);
      return source.replace(FIXED_GUARD, PRE_FIX_GUARD);
    });
    client.input(ORDINARY);
    assert.throws(
      () => client.input(OVERFLOW),
      // Cross-realm throw: assert on the error's own shape, not host instanceof.
      (error) => error && error.name === 'TypeError' && /toLocaleString/.test(error.message),
      `${path}: the bug must be observable without the guard`,
    );
  });
}

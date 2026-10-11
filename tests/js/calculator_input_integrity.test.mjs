/**
 * Node replica of calculator parseNum / compute / curveGeometry from
 * templates/calculators/{compounding,dollar_cost_averaging}.html.j2.
 *
 * Pins whole-token number parsing, bilingual domain/overflow messages,
 * WORKED_EXAMPLES, and compounding chart geometry (time-based x, t=0 point).
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const COMP_PATH = join(ROOT, 'templates', 'calculators', 'compounding.html.j2');
const DCA_PATH = join(ROOT, 'templates', 'calculators', 'dollar_cost_averaging.html.j2');
const COMP_SRC = readFileSync(COMP_PATH, 'utf8');
const DCA_SRC = readFileSync(DCA_PATH, 'utf8');

function isIdent(ch) {
  return /[A-Za-z0-9_$]/.test(ch);
}

/** Brace-match a `function name(` declaration, skipping strings, comments, regex. */
function extractFunction(source, name) {
  const needle = `function ${name}(`;
  const start = source.indexOf(needle);
  if (start < 0) throw new Error(`${name}() not found`);
  const brace = source.indexOf('{', start);
  if (brace < 0) throw new Error(`${name}() opening brace not found`);
  const end = matchBlock(source, brace);
  return source.slice(start, end + 1);
}

function extractVarDecl(source, name) {
  const re = new RegExp(`\\bvar\\s+${name}\\s*=\\s*[^;]+;`);
  const m = source.match(re);
  if (!m) throw new Error(`var ${name} not found`);
  return m[0];
}

function matchBlock(source, braceIdx) {
  let depth = 0;
  let i = braceIdx;
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
    if (ch === '/' && isRegexStart(source, i)) {
      i = skipRegex(source, i);
      continue;
    }
    if (ch === '{') depth += 1;
    else if (ch === '}') {
      depth -= 1;
      if (depth === 0) return i;
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

function skipRegex(source, i) {
  i += 1;
  while (i < source.length) {
    if (source[i] === '\\') {
      i += 2;
      continue;
    }
    if (source[i] === '/') {
      i += 1;
      while (i < source.length && /[a-z]/i.test(source[i])) i += 1;
      return i;
    }
    if (source[i] === '\n') return i;
    i += 1;
  }
  return i;
}

function isRegexStart(source, i) {
  let j = i - 1;
  while (j >= 0 && /[ \t\n\r]/.test(source[j])) j -= 1;
  if (j < 0) return true;
  const prev = source[j];
  if (isIdent(prev) || prev === ')' || prev === ']' || prev === '}') return false;
  return true;
}

function loadTemplate(source, names) {
  const parts = [];
  let limitSrc = null;
  try {
    limitSrc = extractVarDecl(source, 'LIMIT');
    parts.push(limitSrc);
  } catch {
    // LIMIT may be missing on unmodified main; overflow tests still drive compute.
  }
  for (const name of names) {
    const fnSrc = extractFunction(source, name);
    parts.push(fnSrc);
  }
  const context = vm.createContext({
    Math,
    Number,
    String,
    isFinite,
    parseFloat,
    parseInt,
    Infinity,
    NaN,
    console,
  });
  vm.runInContext(parts.join('\n'), context);
  const out = { LIMIT: context.LIMIT };
  for (const name of names) out[name] = context[name];
  return out;
}

const ACCEPT = [
  ['1500', 'num', 1500],
  ['1,500', 'num', 1500],
  ['1,500.50', 'num', 1500.5],
  ['1,000,000', 'num', 1000000],
  ['.5', 'num', 0.5],
  ['5.', 'num', 5],
  ['+5', 'num', 5],
  ['-3', 'num', -3],
  ['007', 'num', 7],
  [' 42 ', 'num', 42],
  ['7%', 'pct', 7],
  ['7 %', 'pct', 7],
];

const REJECT_FORMAT = [
  ['12abc', 'num'],
  ['1,2,3', 'num'],
  ['1,23', 'num'],
  ['1000,000', 'num'],
  ['1,0000', 'num'],
  ['1e5', 'num'],
  ['1.2.3', 'num'],
  ['1 000', 'num'],
  ['Infinity', 'num'],
  ['NaN', 'num'],
  ['0x10', 'num'],
  ['.', 'num'],
  ['-', 'num'],
  ['$500', 'num'],
  ['%7', 'num'],
  ['１２', 'num'],
  ['7%', 'num'],
  ['1,5', 'num'],
];

const RANGE_RAW = '9'.repeat(400);

function parseNumSrcOf(source) {
  return extractFunction(source, 'parseNum');
}

test('parseNum source text is byte-identical in both templates', () => {
  assert.equal(parseNumSrcOf(COMP_SRC), parseNumSrcOf(DCA_SRC));
});

function runParseTable(label, source) {
  test(`${label} parseNum accept table`, () => {
    const { parseNum } = loadTemplate(source, ['parseNum']);
    for (const [raw, unit, want] of ACCEPT) {
      const got = parseNum(raw, unit);
      assert.equal(got.ok, true, `${raw} unit=${unit} should accept`);
      assert.equal(got.v, want, `${raw} unit=${unit} value`);
    }
  });

  test(`${label} parseNum reject format table`, () => {
    const { parseNum } = loadTemplate(source, ['parseNum']);
    for (const [raw, unit] of REJECT_FORMAT) {
      const got = parseNum(raw, unit);
      assert.equal(got.ok, false, `${raw} unit=${unit} should reject`);
      assert.equal(got.why, 'format', `${raw} unit=${unit} why`);
    }
    const blank = parseNum('', 'num');
    assert.equal(blank.ok, false);
    assert.equal(blank.why, 'blank');
    const nul = parseNum(null, 'num');
    assert.equal(nul.ok, false);
    assert.equal(nul.why, 'blank');
  });

  test(`${label} parseNum reject range (400 nines)`, () => {
    const { parseNum } = loadTemplate(source, ['parseNum']);
    const got = parseNum(RANGE_RAW, 'num');
    assert.equal(got.ok, false);
    assert.equal(got.why, 'range');
  });
}

runParseTable('compounding', COMP_SRC);
runParseTable('dca', DCA_SRC);

test('compounding compute WORKED_EXAMPLES {P:10000,c:500,f:12,r:7,n:10} FV 106638.65 ±1 (self-check band)', () => {
  const { compute } = loadTemplate(COMP_SRC, ['compute']);
  const got = compute({ P: 10000, c: 500, f: 12, r: 7, n: 10 });
  assert.equal(got.ok, true);
  assert.ok(Math.abs(got.FV - 106638.65) <= 1, `FV=${got.FV}`);
});

test('dca compute WORKED_EXAMPLES {c:500,f:12,yrs:5,r:8} and zero-return', () => {
  const { compute } = loadTemplate(DCA_SRC, ['compute']);
  const a = compute({ c: 500, f: 12, yrs: 5, r: 8 });
  assert.equal(a.ok, true);
  assert.equal(a.N, 60);
  assert.ok(Math.abs(a.fv - 36738) <= 1, `fv=${a.fv}`);
  assert.equal(a.invested, 30000);
  assert.ok(Math.abs(a.gain - 6738) <= 1, `gain=${a.gain}`);
  const b = compute({ c: 200, f: 12, yrs: 10, r: 0 });
  assert.equal(b.ok, true);
  assert.equal(b.N, 120);
  assert.equal(b.fv, 24000);
  assert.equal(b.invested, 24000);
  assert.equal(b.gain, 0);
});

function assertBiMsg(res, note) {
  assert.equal(res.ok, false, note);
  assert.equal(typeof res.msg, 'object', `${note}: msg is object, got ${typeof res.msg}`);
  assert.equal(typeof res.msg.en, 'string', `${note}: msg.en`);
  assert.equal(typeof res.msg.zh, 'string', `${note}: msg.zh`);
  assert.ok(res.msg.en.length > 0, `${note}: en non-empty`);
  assert.ok(res.msg.zh.length > 0, `${note}: zh non-empty`);
}

test('compounding compute failure msgs are bilingual objects', () => {
  const { compute } = loadTemplate(COMP_SRC, ['compute']);
  const branches = [
    [{ P: NaN, c: 0, f: 12, r: 7, n: 10 }, 'principal'],
    [{ P: 1000, c: NaN, f: 12, r: 7, n: 10 }, 'contrib'],
    [{ P: 1000, c: 0, f: 0, r: 7, n: 10 }, 'freq'],
    [{ P: 1000, c: 0, f: 12, r: NaN, n: 10 }, 'rate'],
    [{ P: 1000, c: 0, f: 12, r: 7, n: 0 }, 'years-min'],
    [{ P: 1000, c: 0, f: 12, r: 7, n: 51 }, 'years-max'],
  ];
  for (const [inp, name] of branches) assertBiMsg(compute(inp), name);
});

test('dca compute failure msgs are bilingual objects', () => {
  const { compute } = loadTemplate(DCA_SRC, ['compute']);
  const branches = [
    [{ c: 0, f: 12, yrs: 5, r: 8 }, 'contrib'],
    [{ c: 500, f: 0, yrs: 5, r: 8 }, 'freq'],
    [{ c: 500, f: 12, yrs: 0, r: 8 }, 'years'],
    [{ c: 500, f: 12, yrs: 5, r: NaN }, 'rate'],
    [{ c: 500, f: 12, yrs: 0.01, r: 8 }, 'horizon-too-short'],
  ];
  for (const [inp, name] of branches) assertBiMsg(compute(inp), name);
});

test('overflow is withheld: compounding 1e300 / 1e14@100% and dca 1e300', () => {
  const { compute: cComp } = loadTemplate(COMP_SRC, ['compute']);
  const a = cComp({ P: 1e300, c: 0, f: 12, r: 7, n: 50 });
  assert.equal(a.ok, false, 'compounding P=1e300 should withhold');
  assertBiMsg(a, 'compounding-1e300');
  const b = cComp({ P: 1e14, c: 0, f: 12, r: 100, n: 50 });
  assert.equal(b.ok, false, 'compounding P=1e14 r=100 n=50 should withhold');
  assertBiMsg(b, 'compounding-1e14');
  const { compute: cDca } = loadTemplate(DCA_SRC, ['compute']);
  const d = cDca({ c: 1e300, f: 12, yrs: 5, r: 8 });
  assert.equal(d.ok, false, 'dca c=1e300 should withhold');
  assertBiMsg(d, 'dca-1e300');
});

test('curveGeometry 1-year: x 40.0/580.0, finite, last fv ≈ 1104.71', () => {
  const { compute, curveGeometry } = loadTemplate(COMP_SRC, ['compute', 'curveGeometry']);
  const res = compute({ P: 1000, c: 0, f: 12, r: 10, n: 1 });
  assert.equal(res.ok, true);
  assert.ok(Math.abs(res.FV - 1104.71) < 0.02, `FV=${res.FV}`);
  const g = curveGeometry(1000, res.rows);
  assert.equal(g.pts.length, 2);
  assert.equal(g.pts[0].x, 40.0);
  assert.equal(g.pts[1].x, 580.0);
  for (const p of g.pts) {
    assert.equal(Number.isFinite(p.x), true);
    assert.equal(Number.isFinite(p.yFv), true);
    assert.equal(Number.isFinite(p.yC), true);
  }
  for (const d of [g.lineFv, g.lineC, g.areaFv, g.areaC]) {
    assert.equal(/NaN|Infinity/.test(d), false, d);
  }
  assert.ok(Math.abs(res.rows[res.rows.length - 1].fv - res.FV) < 1e-9);
});

test('curveGeometry 2.5-year: x 40.0, 256.0, 472.0, 580.0', () => {
  const { compute, curveGeometry } = loadTemplate(COMP_SRC, ['compute', 'curveGeometry']);
  const res = compute({ P: 1000, c: 100, f: 12, r: 5, n: 2.5 });
  assert.equal(res.ok, true);
  const g = curveGeometry(1000, res.rows);
  const xs = Array.from(g.pts, (p) => Number(p.x));
  assert.equal(xs.length, 4);
  assert.equal(xs[0], 40.0);
  assert.equal(xs[1], 256.0);
  assert.equal(xs[2], 472.0);
  assert.equal(xs[3], 580.0);
});

test('curveGeometry all-zero: every y is 172.0, no NaN/Infinity in paths', () => {
  const { compute, curveGeometry } = loadTemplate(COMP_SRC, ['compute', 'curveGeometry']);
  const res = compute({ P: 0, c: 0, f: 12, r: 7, n: 3 });
  assert.equal(res.ok, true);
  const g = curveGeometry(0, res.rows);
  for (const p of g.pts) {
    assert.equal(p.yFv, 172.0);
    assert.equal(p.yC, 172.0);
  }
  for (const d of [g.lineFv, g.lineC, g.areaFv, g.areaC]) {
    assert.equal(/NaN|Infinity/.test(d), false, d);
  }
});

test('curveGeometry last point yFv is 24.0 when FV>0', () => {
  const { compute, curveGeometry } = loadTemplate(COMP_SRC, ['compute', 'curveGeometry']);
  const res = compute({ P: 1000, c: 0, f: 12, r: 10, n: 5 });
  assert.equal(res.ok, true);
  assert.ok(res.FV > 0);
  const g = curveGeometry(1000, res.rows);
  assert.equal(g.pts[g.pts.length - 1].yFv, 24.0);
});

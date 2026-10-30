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
const TEMPLATE_DIR = process.env.CALC_TEMPLATE_DIR || join(ROOT, 'templates', 'calculators');
const COMP_PATH = join(TEMPLATE_DIR, 'compounding.html.j2');
const DCA_PATH = join(TEMPLATE_DIR, 'dollar_cost_averaging.html.j2');
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

function srcOf(source, name) {
  return extractFunction(source, name);
}

test('curLang, echoNum and tryCopy source text is byte-identical in both templates', () => {
  for (const name of ['curLang', 'echoNum', 'tryCopy', 'showCopyFallback']) {
    assert.equal(srcOf(COMP_SRC, name), srcOf(DCA_SRC, name), name);
  }
});

const LATIN_WORD = /[A-Za-z]{2,}/;
const URLISH = /https?:|www\.|\.com\b|[?&][A-Za-z_]+=/;

test('plainSentence EN matches worked-example English; ZH keeps numbers and has no latin words', () => {
  const { plainSentence: dcaPlain } = loadTemplate(DCA_SRC, ['plainSentence']);
  const dcaD = { c: '$500', N: '60', fv: '$36,738', invested: '$30,000', gain: '$6,738' };
  const dca = dcaPlain(dcaD);
  assert.equal(
    dca.en,
    'Investing $500 across 60 buys projects to $36,738 — $30,000 invested plus $6,738 of growth at this hypothetical rate.',
  );
  for (const n of Object.values(dcaD)) assert.ok(dca.zh.includes(n), `dca zh missing ${n}`);
  let dcaZhRest = dca.zh;
  for (const n of Object.values(dcaD)) dcaZhRest = dcaZhRest.split(n).join('');
  assert.equal(LATIN_WORD.test(dcaZhRest), false, dcaZhRest);

  const { plainSentence: compPlain } = loadTemplate(COMP_SRC, ['plainSentence']);
  const compD = { n: '10', contributed: '$70,000', fv: '$106,639', growth: '$36,639' };
  const comp = compPlain(compD);
  assert.equal(
    comp.en,
    'After 10 years, $70,000 in contributions grow to $106,639 — the extra $36,639 is compounding doing the work.',
  );
  for (const n of Object.values(compD)) assert.ok(comp.zh.includes(n), `comp zh missing ${n}`);
  let compZhRest = comp.zh;
  for (const n of Object.values(compD)) compZhRest = compZhRest.split(n).join('');
  assert.equal(LATIN_WORD.test(compZhRest), false, compZhRest);
});

test('plainSentence EN compounding 1-year scenario uses singular year', () => {
  const { plainSentence: compPlain } = loadTemplate(COMP_SRC, ['plainSentence']);
  const one = compPlain({ n: '1', contributed: '$1,000', fv: '$1,105', growth: '$105' });
  assert.ok(one.en.startsWith('After 1 year, '), one.en);
});

test('copyText includes identity, inputs, results; ZH has no latin; neither language has a URL', () => {
  const { copyText: dcaCopy } = loadTemplate(DCA_SRC, ['copyText']);
  const dcaEnD = {
    contrib: '$500', freq: 'Monthly', years: '5', rate: '8',
    fv: '$36,738', invested: '$30,000', gain: '$6,738', ret: '22%', buys: '60',
  };
  const dcaZhD = { ...dcaEnD, freq: '每月' };
  const dcaEn = dcaCopy('en', dcaEnD);
  const dcaZh = dcaCopy('zh', dcaZhD);
  assert.ok(dcaEn.includes('Mastermind dollar-cost averaging calculator (hypothetical scenario)'));
  assert.ok(dcaZh.includes('Mastermind 定投计算器（假设情景）'));
  for (const v of Object.values(dcaEnD)) assert.ok(dcaEn.includes(v), `dca en missing ${v}`);
  for (const v of Object.values(dcaZhD)) assert.ok(dcaZh.includes(v), `dca zh missing ${v}`);
  assert.ok(dcaEn.includes('years') && dcaEn.includes('8%'));
  assert.ok(dcaZh.includes('年') && dcaZh.includes('8%'));
  assert.equal(LATIN_WORD.test(dcaZh.replace(/Mastermind/g, '')), false, dcaZh);
  assert.equal(URLISH.test(dcaEn), false, dcaEn);
  assert.equal(URLISH.test(dcaZh), false, dcaZh);

  const { copyText: compCopy } = loadTemplate(COMP_SRC, ['copyText']);
  const compEnD = {
    principal: '$10,000', contrib: '$500', freq: 'Monthly', rate: '7', years: '10',
    fv: '$106,639', contributed: '$70,000', growth: '$36,639', mult: '1.52×',
  };
  const compZhD = { ...compEnD, freq: '每月' };
  const compEn = compCopy('en', compEnD);
  const compZh = compCopy('zh', compZhD);
  assert.ok(compEn.includes('Mastermind compound interest calculator (hypothetical scenario)'));
  assert.ok(compZh.includes('Mastermind 复利计算器（假设情景）'));
  for (const v of Object.values(compEnD)) assert.ok(compEn.includes(v), `comp en missing ${v}`);
  for (const v of Object.values(compZhD)) assert.ok(compZh.includes(v), `comp zh missing ${v}`);
  assert.ok(compEn.includes('years') && compEn.includes('7%'));
  assert.ok(compZh.includes('年') && compZh.includes('7%'));
  assert.equal(LATIN_WORD.test(compZh.replace(/Mastermind/g, '')), false, compZh);
  assert.equal(URLISH.test(compEn), false, compEn);
  assert.equal(URLISH.test(compZh), false, compZh);
});

function makeDocument(execImpl) {
  const ta = { value: '', setAttribute() {}, select() {} };
  return {
    createElement() { return ta; },
    body: { appendChild() {}, removeChild() {} },
    execCommand: execImpl,
  };
}

function loadTryCopy(source, extras) {
  const fnSrc = extractFunction(source, 'tryCopy');
  const context = vm.createContext({
    Promise,
    Error,
    document: extras.document,
    navigator: extras.navigator,
  });
  vm.runInContext(fnSrc, context);
  return context.tryCopy;
}

function makeFakeTextarea(contentLines) {
  const ta = {
    value: '',
    rows: 4,
    scrollTop: 0,
    selectionStart: 0,
    selectionEnd: 0,
    focusCalls: [],
    focus(opts) {
      this.focusCalls.push(opts);
    },
    select() {
      this.selectionStart = 0;
      this.selectionEnd = this.value.length;
      this.scrollTop = this.scrollHeight - this.clientHeight;
    },
  };
  Object.defineProperty(ta, 'clientHeight', {
    get() { return this.rows * 21; },
  });
  Object.defineProperty(ta, 'scrollHeight', {
    get() { return contentLines * 21; },
  });
  return ta;
}

function makeFakeBox() {
  return {
    hidden: true,
    scrollIntoViewArgs: [],
    scrollIntoView(args) {
      this.scrollIntoViewArgs.push(args);
    },
  };
}

test('showCopyFallback grows rows, resets scrollTop, focuses and selects', () => {
  const { showCopyFallback } = loadTemplate(DCA_SRC, ['showCopyFallback']);
  const sixText = 'L1\nL2\nL3\nL4\nL5\nL6';
  const ta6 = makeFakeTextarea(6);
  const box6 = makeFakeBox();
  showCopyFallback(box6, ta6, sixText);
  assert.equal(ta6.rows, 6);
  assert.equal(ta6.scrollTop, 0);
  assert.equal(ta6.focusCalls.length > 0, true);
  assert.equal(ta6.selectionStart, 0);
  assert.equal(ta6.selectionEnd, sixText.length);
  assert.equal(box6.hidden, false);
  assert.equal(box6.scrollIntoViewArgs.length, 1);
  assert.equal(box6.scrollIntoViewArgs[0].block, 'center');

  const twelveText = Array.from({ length: 12 }, (_, i) => `L${i + 1}`).join('\n');
  const ta12 = makeFakeTextarea(12);
  const box12 = makeFakeBox();
  showCopyFallback(box12, ta12, twelveText);
  assert.equal(ta12.rows, 8);
  assert.equal(ta12.scrollTop, 0);
});

test('compounding compute domain errors name the responsible field', () => {
  const { compute } = loadTemplate(COMP_SRC, ['compute']);
  assert.equal(compute({ P: -5, c: 0, f: 12, r: 7, n: 10 }).field, 'principal');
  assert.equal(compute({ P: 1000, c: -1, f: 12, r: 7, n: 10 }).field, 'contrib');
  assert.equal(compute({ P: 1000, c: 0, f: 12, r: -1, n: 10 }).field, 'rate');
  assert.equal(compute({ P: 1000, c: 0, f: 12, r: 7, n: 0 }).field, 'years');
  assert.equal(compute({ P: 1000, c: 0, f: 12, r: 7, n: 60 }).field, 'years');
  assert.equal(compute({ P: 1000, c: 0, f: 0, r: 7, n: 10 }).field, undefined);
  const overflow = compute({ P: 1e300, c: 0, f: 12, r: 7, n: 50 });
  assert.equal(overflow.ok, false);
  assert.equal(overflow.field, undefined);
});

test('dca compute domain errors name the responsible field', () => {
  const { compute } = loadTemplate(DCA_SRC, ['compute']);
  assert.equal(compute({ c: 0, f: 12, yrs: 5, r: 8 }).field, 'contrib');
  assert.equal(compute({ c: 500, f: 12, yrs: 0, r: 8 }).field, 'years');
  assert.equal(compute({ c: 500, f: 12, yrs: 5, r: NaN }).field, 'rate');
  assert.equal(compute({ c: 500, f: 12, yrs: 0.01, r: 8 }).field, 'years');
  assert.equal(compute({ c: 500, f: 0, yrs: 5, r: 8 }).field, undefined);
  const overflow = compute({ c: 1e300, f: 12, yrs: 5, r: 8 });
  assert.equal(overflow.ok, false);
  assert.equal(overflow.field, undefined);
});

test('tryCopy reports success only on an acknowledged write', async () => {
  const src = DCA_SRC;
  const t1 = loadTryCopy(src, {
    navigator: { clipboard: { writeText: () => Promise.resolve() } },
    document: makeDocument(() => true),
  });
  assert.equal(await t1('x'), true);

  const t2 = loadTryCopy(src, {
    navigator: { clipboard: { writeText: () => Promise.reject(new Error('denied')) } },
    document: makeDocument(() => false),
  });
  assert.equal(await t2('x'), false);

  const t3 = loadTryCopy(src, {
    navigator: { clipboard: { writeText: () => { throw new Error('sync'); } } },
    document: makeDocument(() => false),
  });
  assert.equal(await t3('x'), false);

  const t4 = loadTryCopy(src, {
    navigator: {},
    document: makeDocument(() => false),
  });
  assert.equal(await t4('x'), false);

  const t5 = loadTryCopy(src, {
    navigator: {},
    document: makeDocument(() => true),
  });
  assert.equal(await t5('x'), true);

  const t6 = loadTryCopy(src, {
    navigator: {},
    document: makeDocument(() => { throw new Error('exec'); }),
  });
  assert.equal(await t6('x'), false);
});


/*
 * Clipboard-feedback lifetime regression: execute the unchanged, whole
 * compounding inline script in a minimal event-driven DOM/clipboard VM.
 * Deferred promises and controlled timers make stale callbacks deterministic.
 */
const COMP_SCRIPT_BLOCK = COMP_SRC.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(COMP_SCRIPT_BLOCK, 'compounding inline script should exist');

function makeCompoundingCopyPage(options = {}) {
  const nodes = new Map();
  const documentEvents = new Map();
  const clipboardWrites = [];
  const legacyWrites = [];
  const timers = [];
  const errors = [];

  function node(id) {
    const handlers = new Map();
    const attrs = new Map();
    const classes = new Set();
    return {
      id, value: '', hidden: false, rows: 4, scrollTop: 0,
      selectionStart: 0, selectionEnd: 0, textContent: '', innerHTML: '',
      style: {}, children: [], dataset: {}, className: '',
      classList: {
        add(name) { classes.add(name); },
        remove(name) { classes.delete(name); },
        contains(name) { return classes.has(name); },
      },
      addEventListener(name, fn) { handlers.set(name, fn); },
      fire(name, event = {}) {
        assert.ok(handlers.has(name), id + ' has ' + name + ' listener');
        handlers.get(name)(event);
      },
      getAttribute(name) { return attrs.has(name) ? attrs.get(name) : null; },
      setAttribute(name, value) { attrs.set(name, String(value)); },
      removeAttribute(name) { attrs.delete(name); },
      appendChild(child) { this.children.push(child); },
      focus() { this.focused = true; },
      select() {
        this.selectionStart = 0;
        this.selectionEnd = this.value.length;
        this.scrollTop = this.scrollHeight - this.clientHeight;
      },
      scrollIntoView() { this.scrolledIntoView = true; },
      querySelectorAll() { return []; },
      getTotalLength() { return 600; },
      get scrollHeight() { return this.value.split('\n').length * 21; },
      get clientHeight() { return this.rows * 21; },
    };
  }

  for (const id of [
    'principal', 'contrib', 'rate', 'years', 'out-main', 'out-plain',
    'out-contrib', 'out-growth', 'out-mult', 'year-tbody',
    'year-table-wrap', 'freq-seg', 'copy-result', 'copied',
    'copy-fallback', 'copy-fallback-text', 'curve-wrap',
    'cp-area-fv', 'cp-area-c', 'cp-line-fv', 'cp-line-c',
  ]) nodes.set(id, node(id));

  const initial = { principal: '10000', contrib: '500', rate: '7', years: '10' };
  for (const [name, value] of Object.entries(initial)) nodes.get(name).value = value;
  nodes.get('copy-fallback').hidden = true;
  const documentElement = node('html');
  documentElement.setAttribute('data-lang', 'en');
  const document = {
    documentElement,
    getElementById(id) { assert.ok(nodes.has(id), 'unknown DOM id ' + id); return nodes.get(id); },
    createElement(tag) { return node(tag); },
    addEventListener(name, fn) { documentEvents.set(name, fn); },
    body: { appendChild() {}, removeChild() {} },
    execCommand(command) {
      assert.equal(command, 'copy');
      legacyWrites.push(command);
      return options.legacySuccess === true;
    },
  };
  const navigator = options.clipboardAvailable === false ? {} : {
    clipboard: {
      writeText(value) {
        return new Promise((resolve, reject) => {
          clipboardWrites.push({ value, resolve, reject });
        });
      },
    },
  };
  const context = vm.createContext({
    document, navigator,
    window: { matchMedia: () => ({ matches: true }) },
    Promise, Math, Number, String, isFinite, parseInt, console: {
      error(...args) { errors.push(args); },
    },
    setTimeout(fn, ms) {
      const timer = { fn, ms, active: true };
      timers.push(timer);
      return timers.length;
    },
    clearTimeout(id) {
      if (timers[id - 1]) timers[id - 1].active = false;
    },
  });
  vm.runInContext(COMP_SCRIPT_BLOCK[1], context, { filename: COMP_PATH });
  assert.ok(documentEvents.has('DOMContentLoaded'));
  documentEvents.get('DOMContentLoaded')();
  assert.deepEqual(errors, [], 'page self-check');

  return {
    get(id) { return nodes.get(id); },
    clipboardWrites, legacyWrites, timers,
    click() { nodes.get('copy-result').fire('click'); },
    input(id, value) {
      nodes.get(id).value = value;
      nodes.get(id).fire('input');
    },
    frequency(value) {
      const btn = node('frequency');
      btn.dataset.v = String(value);
      nodes.get('freq-seg').fire('click', { target: { closest() { return btn; } } });
    },
    language(value) {
      documentElement.setAttribute('data-lang', value);
      documentEvents.get('langchange')();
    },
    succeed(index) { clipboardWrites[index].resolve(); },
    reject(index) { clipboardWrites[index].reject(new Error('clipboard denied')); },
    showCopied() { return nodes.get('copied').classList.contains('show'); },
    fallbackShown() { return !nodes.get('copy-fallback').hidden; },
    async flush() {
      for (let i = 0; i < 6; i += 1) await Promise.resolve();
    },
  };
}

test('compounding generated page includes byte-identical calculator inline script', () => {
  const built = readFileSync(join(ROOT, 'site', 'tools', 'calculators', 'compounding.html'), 'utf8');
  assert.ok(built.includes(COMP_SCRIPT_BLOCK[0]), 'generated page has exact template inline script');
});

test('compounding obsolete rejection after input edit never reopens old fallback', async () => {
  const ui = makeCompoundingCopyPage();
  ui.click();
  assert.match(ui.clipboardWrites[0].value, /\$10,000/);
  ui.input('principal', '20000');
  assert.match(ui.get('out-main').textContent, /^\$/);
  ui.reject(0);
  await ui.flush();
  assert.equal(ui.fallbackShown(), false);
  assert.equal(ui.get('copy-fallback-text').value, '');
  assert.equal(ui.showCopied(), false);
});

test('compounding second success survives first attempt rejection', async () => {
  const ui = makeCompoundingCopyPage();
  ui.click();
  ui.click();
  ui.succeed(1);
  await ui.flush();
  assert.equal(ui.showCopied(), true);
  ui.reject(0);
  await ui.flush();
  assert.equal(ui.showCopied(), true);
  assert.equal(ui.fallbackShown(), false);
});

test('compounding old success cannot appear beside newly invalid result', async () => {
  const ui = makeCompoundingCopyPage();
  ui.click();
  ui.input('principal', '');
  assert.equal(ui.get('out-main').textContent, '—');
  ui.succeed(0);
  await ui.flush();
  assert.equal(ui.showCopied(), false);
  assert.equal(ui.fallbackShown(), false);
  ui.click();
  assert.equal(ui.clipboardWrites.length, 1, 'invalid result cannot be copied');
});

test('compounding frequency change invalidates pending success and completed feedback', async () => {
  const ui = makeCompoundingCopyPage();
  ui.click();
  ui.frequency(4);
  ui.succeed(0);
  await ui.flush();
  assert.equal(ui.showCopied(), false);
  ui.click();
  assert.match(ui.clipboardWrites[1].value, /Quarterly/);
  ui.succeed(1);
  await ui.flush();
  assert.equal(ui.showCopied(), true);
  ui.frequency(1);
  assert.equal(ui.showCopied(), false);
  assert.equal(ui.fallbackShown(), false);
});

test('compounding language change invalidates pending failure and copies current language', async () => {
  const ui = makeCompoundingCopyPage();
  ui.click();
  ui.language('zh');
  ui.reject(0);
  await ui.flush();
  assert.equal(ui.fallbackShown(), false);
  ui.click();
  assert.match(ui.clipboardWrites[1].value, /复利计算器/);
  ui.succeed(1);
  await ui.flush();
  assert.equal(ui.showCopied(), true);
  ui.language('en');
  assert.equal(ui.showCopied(), false);
});

test('compounding older success timer cannot erase newer attempt feedback', async () => {
  const ui = makeCompoundingCopyPage();
  ui.click();
  ui.succeed(0);
  await ui.flush();
  assert.equal(ui.showCopied(), true);
  assert.equal(ui.timers.length, 1);
  ui.click();
  ui.succeed(1);
  await ui.flush();
  assert.equal(ui.timers.length, 2);
  assert.equal(ui.timers[0].active, false, 'older timer canceled');
  ui.timers[0].fn(); // simulate a callback already queued before cancellation
  assert.equal(ui.showCopied(), true, 'obsolete timer must not clear newer Copied');
  ui.timers[1].fn();
  assert.equal(ui.showCopied(), false, 'latest timeout clears current Copied');
});

test('compounding input edit removes displayed feedback and defuses its timer', async () => {
  const ui = makeCompoundingCopyPage();
  ui.click();
  ui.succeed(0);
  await ui.flush();
  assert.equal(ui.showCopied(), true);
  ui.input('years', '11');
  assert.equal(ui.showCopied(), false);
  assert.equal(ui.timers[0].active, false);
  ui.timers[0].fn();
  assert.equal(ui.showCopied(), false);
});

test('compounding latest rejected copy shows readable selectable click-time fallback', async () => {
  const ui = makeCompoundingCopyPage({ legacySuccess: false });
  ui.click();
  const clicked = ui.clipboardWrites[0].value;
  ui.reject(0);
  await ui.flush();
  const textarea = ui.get('copy-fallback-text');
  assert.equal(ui.fallbackShown(), true);
  assert.equal(ui.showCopied(), false);
  assert.equal(textarea.value, clicked);
  assert.equal(textarea.focused, true);
  assert.equal(textarea.selectionStart, 0);
  assert.equal(textarea.selectionEnd, clicked.length);
  assert.equal(textarea.scrollTop, 0);
});

test('compounding unavailable clipboard preserves successful legacy copy feedback', async () => {
  const ui = makeCompoundingCopyPage({ clipboardAvailable: false, legacySuccess: true });
  ui.click();
  await ui.flush();
  assert.equal(ui.legacyWrites.length, 1);
  assert.equal(ui.showCopied(), true);
  assert.equal(ui.fallbackShown(), false);
});

test('compounding unavailable clipboard preserves failed legacy fallback', async () => {
  const ui = makeCompoundingCopyPage({ clipboardAvailable: false, legacySuccess: false });
  ui.click();
  await ui.flush();
  assert.equal(ui.legacyWrites.length, 1);
  assert.equal(ui.showCopied(), false);
  assert.equal(ui.fallbackShown(), true);
  assert.match(ui.get('copy-fallback-text').value, /hypothetical scenario/);
});

test('compounding rejected async clipboard uses successful legacy copy', async () => {
  const ui = makeCompoundingCopyPage({ legacySuccess: true });
  ui.click();
  ui.reject(0);
  await ui.flush();
  assert.equal(ui.legacyWrites.length, 1);
  assert.equal(ui.showCopied(), true);
  assert.equal(ui.fallbackShown(), false);
});

test('compounding newer failed attempt supersedes an older pending success', async () => {
  const ui = makeCompoundingCopyPage({ legacySuccess: false });
  ui.click();
  ui.input('principal', '20000');
  ui.click();
  assert.match(ui.clipboardWrites[0].value, /\$10,000/);
  assert.match(ui.clipboardWrites[1].value, /\$20,000/);
  ui.reject(1);
  await ui.flush();
  assert.equal(ui.fallbackShown(), true);
  assert.equal(ui.get('copy-fallback-text').value, ui.clipboardWrites[1].value);
  ui.succeed(0);
  await ui.flush();
  assert.equal(ui.fallbackShown(), true, 'older success does not hide latest fallback');
  assert.equal(ui.showCopied(), false);
});


test('compounding obsolete rejected copy never triggers a new legacy clipboard write', async () => {
  const ui = makeCompoundingCopyPage({ legacySuccess: true });
  ui.click();
  ui.input('principal', '20000');
  ui.reject(0);
  await ui.flush();
  assert.equal(ui.legacyWrites.length, 0, 'obsolete rejection must not start execCommand');
  assert.equal(ui.showCopied(), false);
  assert.equal(ui.fallbackShown(), false);
});

test('compounding late rejection cannot overwrite newer successful clipboard write', async () => {
  const ui = makeCompoundingCopyPage({ legacySuccess: true });
  ui.click();
  ui.input('principal', '20000');
  ui.click();
  assert.match(ui.clipboardWrites[0].value, /\$10,000/);
  assert.match(ui.clipboardWrites[1].value, /\$20,000/);
  ui.succeed(1);
  await ui.flush();
  assert.equal(ui.showCopied(), true);
  ui.reject(0);
  await ui.flush();
  assert.equal(ui.legacyWrites.length, 0, 'stale first attempt cannot overwrite clipboard');
  assert.equal(ui.showCopied(), true);
  assert.equal(ui.fallbackShown(), false);
});

test('compounding frequency and language invalidate a late legacy fallback', async () => {
  const ui = makeCompoundingCopyPage({ legacySuccess: true });
  ui.click();
  ui.frequency(4);
  ui.reject(0);
  await ui.flush();
  assert.equal(ui.legacyWrites.length, 0);
  ui.click();
  ui.language('zh');
  ui.reject(1);
  await ui.flush();
  assert.equal(ui.legacyWrites.length, 0);
  assert.equal(ui.fallbackShown(), false);
});

test('compounding latest rejected operation still performs successful legacy copy', async () => {
  const ui = makeCompoundingCopyPage({ legacySuccess: true });
  ui.click();
  ui.reject(0);
  await ui.flush();
  assert.equal(ui.legacyWrites.length, 1, 'current-attempt fallback retained');
  assert.equal(ui.showCopied(), true);
  assert.equal(ui.fallbackShown(), false);
});

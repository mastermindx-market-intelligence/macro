/** Execute both actual compounding controllers. DOM and clipboard are scripted,
 * not browser/OS acceptance. The rounded fractional-period model is retained.
 * Run: node --test tests/js/compounding_stability.test.mjs
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import vm from 'node:vm';
const ROOT = process.env.COMPOUND_TEST_ROOT || join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const PATHS = ['templates/calculators/compounding.html.j2', 'site/tools/calculators/compounding.html'];
function scriptOf(path) {
  const html = readFileSync(join(ROOT, path), 'utf8');
  const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(match => match[1]).filter(body => body.includes('function compute(') && body.includes('function curveGeometry('));
  assert.equal(scripts.length, 1);
  return scripts[0];
}
function apiOf(script) {
  const context = vm.createContext({ document: { addEventListener() {} }, window: {}, console });
  const instrumented = script.replace(/\}\)\(\);\s*$/, 'globalThis.api={compute,curveGeometry,parseNum};})();');
  assert.notEqual(instrumented, script);
  vm.runInContext(instrumented, context);
  return context.api;
}
const standard = {P:10000,c:500,f:12,r:7,n:10};
const scripts = PATHS.map(scriptOf);
test('template and committed page have identical controllers', () => assert.equal(scripts[0], scripts[1]));
function makeCompoundingCopyPage(script, options = {}) {
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
  vm.runInContext(script, context, { filename: "compounding-controller" });
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


for (const [index, script] of scripts.entries()) {
  const prefix = PATHS[index];
  const api = apiOf(script);
  for (const r of [1e-14, 1.44e-13]) {
    test(`${prefix}: tiny rate ${r} retains principal and contributions`, () => {
      const got = api.compute({...standard, r});
      assert.equal(got.ok, true);
      assert.ok(Math.abs(got.FV - 70000) < 1e-8);
      assert.ok(got.growth >= 0);
      assert.equal(got.rows.at(-1).fv, got.FV);
    });
  }
  test(`${prefix}: frequency and integer-horizon matrix preserves all output surfaces`, () => {
    for (const f of [1,4,12]) for (const r of [0,1e-14,1.44e-13,1e-8,.01,1,7,50])
      for (const n of [1,2,10,25,50]) {
        const inp = {...standard,f,r,n};
        const got = api.compute(inp);
        assert.equal(got.ok, true);
        assert.equal(got.contributed, inp.P + inp.c*n*f);
        assert.equal(got.rows.length, n);
        assert.equal(got.rows.at(-1).fv, got.FV);
        for (const row of got.rows) {
          assert.ok(row.growth >= 0);
          assert.equal(row.fv, api.compute({...inp,n:row.year}).FV);
        }
        const geometry = api.curveGeometry(inp.P, got.rows);
        assert.equal(geometry.pts.length, n+1);
        assert.equal(geometry.pts.at(-1).x, 580);
        assert.doesNotMatch(geometry.lineFv, /NaN|Infinity/);
      }
  });
  test(`${prefix}: 500 seeded independent iterative recurrence controls`, () => {
    let seed = 9021109;
    const random = () => ((seed = (Math.imul(seed,1664525)+1013904223)>>>0) / 4294967296);
    for (let j=0;j<500;j++) {
      const inp={P:random()*100000,c:random()*2000,f:[1,4,12][Math.floor(random()*3)],r:random()*12,n:1+Math.floor(random()*50)};
      const got=api.compute(inp); let expected=inp.P;
      for(let k=0;k<inp.n*inp.f;k++) expected=expected*(1+inp.r/100/inp.f)+inp.c;
      assert.equal(got.ok,true);
      assert.ok(Math.abs(got.FV-expected)<=Math.max(1e-7,Math.abs(expected)*2e-12));
    }
  });
  test(`${prefix}: retained parser, invalid input and overflow refusal`, () => {
    for(const [raw,ok] of [['',false],['1suffix',false],['1e-14',false],['0.00000000000001',true],['7%',true],['1,000',true],['1,0',false],['Infinity',false]])
      assert.equal(api.parseNum(raw,'pct').ok,ok);
    for(const change of [{P:-1},{c:-1},{r:-1},{n:0},{n:51},{P:NaN},{c:NaN},{r:NaN},{n:NaN},{P:1e16},{P:1e15,c:500},{r:100000}])
      assert.equal(api.compute({...standard,...change}).ok,false);
    assert.equal(api.compute({...standard,P:1e15,c:0,r:0}).ok,true);
    assert.equal(api.compute({...standard,P:1e15+1,c:0,r:0}).ok,false);
  });
  test(`${prefix}: known rounded fractional-payment policy remains unchanged`, () => {
    for(const f of [1,4,12]) for(const n of [1.01,1.04,1.05,1.125,1.5,49.99]) {
      const got=api.compute({P:0,c:1000,f,r:0,n});
      assert.equal(got.FV,1000*Math.round(n*f));
      assert.equal(got.rows.at(-1).fv,got.FV);
    }
  });
  for(const lang of ['en','zh']) for(const r of ['0','0.00000000000001','0.000000000000144']) {
    test(`${prefix}: ${lang} screen, table, curves and copy retain rate ${r}`, async () => {
      const ui=makeCompoundingCopyPage(script);
      ui.language(lang);ui.input('rate',r);ui.click();
      const expected='$70,000';
      assert.equal(ui.get('out-main').textContent,expected);
      assert.equal(ui.get('out-contrib').textContent,expected);
      assert.equal(ui.get('out-growth').textContent,'$0');
      assert.ok(ui.get('year-tbody').children.at(-1).innerHTML.includes(expected));
      assert.equal(ui.get('cp-line-fv').getAttribute('d'),ui.get('cp-line-c').getAttribute('d'));
      assert.ok(ui.clipboardWrites[0].value.includes(r+'%'));
      assert.ok(ui.clipboardWrites[0].value.includes(expected));
      ui.succeed(0);await ui.flush();assert.equal(ui.showCopied(),true);
    });
  }
  test(`${prefix}: standard output and invalid-to-valid recovery`, async () => {
    const ui=makeCompoundingCopyPage(script);
    assert.equal(ui.get('out-main').textContent,'$106,639');
    for(const rate of ['-1','1suffix','1e-14','100000']) {
      ui.input('rate',rate);const count=ui.clipboardWrites.length;ui.click();
      assert.equal(ui.get('out-main').textContent,'—');assert.equal(ui.clipboardWrites.length,count);
      assert.equal(ui.get('year-table-wrap').style.display,'none');
      assert.equal(ui.get('cp-line-fv').getAttribute('d'),'');
      assert.equal(ui.showCopied(),false);
    }
    ui.input('rate','7');assert.equal(ui.get('out-main').textContent,'$106,639');
    ui.click();ui.succeed(0);await ui.flush();assert.equal(ui.showCopied(),true);
  });
  test(`${prefix}: stale success cannot restore copy feedback after edits`, async () => {
    const ui=makeCompoundingCopyPage(script);ui.click();ui.input('rate','0.00000000000001');
    ui.succeed(0);await ui.flush();assert.equal(ui.showCopied(),false);
  });
  test(`${prefix}: stale rejection cannot request fallback after edits`, async () => {
    const ui=makeCompoundingCopyPage(script,{legacySuccess:true});ui.click();ui.input('rate','0.00000000000001');
    ui.reject(0);await ui.flush();assert.equal(ui.legacyWrites.length,0);
    assert.equal(ui.fallbackShown(),false);assert.equal(ui.showCopied(),false);
  });
  test(`${prefix}: failed current copy exposes precise manual text and clears on invalidation`, async () => {
    const ui=makeCompoundingCopyPage(script);ui.input('rate','0.00000000000001');ui.click();
    ui.reject(0);await ui.flush();assert.equal(ui.fallbackShown(),true);
    assert.ok(ui.get('copy-fallback-text').value.includes('0.00000000000001%'));
    assert.equal(ui.showCopied(),false);ui.input('principal','');
    assert.equal(ui.fallbackShown(),false);assert.equal(ui.get('copy-fallback-text').value,'');
  });
}

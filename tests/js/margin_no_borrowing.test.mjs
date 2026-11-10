/** Execute both actual inline controllers. No browser or OS clipboard is mocked as proven. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import vm from 'node:vm';

const ROOT = process.env.MARGIN_ROOT || resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const paths = ['templates/calculators/margin.html.j2', 'site/tools/calculators/margin.html'];
function script(path) {
  const source = readFileSync(resolve(ROOT, path), 'utf8');
  const scripts = [...source.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  const found = scripts.filter(s => s.includes('function compute(inp)') && s.includes('margin self-check'));
  assert.equal(found.length, 1, 'one exact calculator controller');
  return found[0];
}
function page(path, language = 'en', legacy = false) {
  const nodes = new Map(); const documentEvents = new Map(); const writes = []; const errors = [];
  let lang = language;
  function node(id) {
    const listeners = new Map(); const classes = new Set();
    return { id, value: '', textContent: '', className: '',
      addEventListener: (type, fn) => listeners.set(type, fn),
      fire: (type) => { assert.ok(listeners.has(type), `${id} ${type}`); listeners.get(type)(); },
      classList: { add: s => classes.add(s), remove: s => classes.delete(s) },
      select() {},
    };
  }
  for (const id of ['equity', 'initial', 'maint', 'price', 'out-main', 'out-plain', 'out-lev', 'out-shares', 'out-pos', 'out-call', 'copy-result', 'copied']) nodes.set(id, node(id));
  let selected = null;
  const document = {
    documentElement: { getAttribute: name => { assert.equal(name, 'data-lang'); return lang; } },
    getElementById: id => { assert.ok(nodes.has(id), id); return nodes.get(id); },
    addEventListener: (type, fn) => documentEvents.set(type, fn),
    createElement: tag => { assert.equal(tag, 'textarea'); return node(tag); },
    body: { appendChild: n => { selected = n; }, removeChild: () => { selected = null; } },
    execCommand: type => { assert.equal(type, 'copy'); writes.push(selected.value); return true; },
  };
  const navigator = legacy ? {} : { clipboard: { writeText: text => { writes.push(text); return Promise.resolve(); } } };
  vm.runInNewContext(script(path), { document, navigator, console: { error: (...a) => errors.push(a) }, setTimeout() {} }, {filename: path});
  documentEvents.get('DOMContentLoaded')();
  assert.deepEqual(errors, [], 'canonical worked examples remain valid');
  return {
    get: id => nodes.get(id).textContent,
    values: () => ['equity', 'initial', 'maint', 'price'].map(id => nodes.get(id).value),
    set(values) { for (const [id, value] of Object.entries(values)) { nodes.get(id).value = String(value); nodes.get(id).fire('input'); } },
    language(value) { lang = value; if (documentEvents.has('langchange')) documentEvents.get('langchange')(); },
    copy() { nodes.get('copy-result').fire('click'); return writes.at(-1); },
    writes,
  };
}
const base = { equity: 10000, initial: 100, maint: 25, price: 50 };
const money = n => '$' + n.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});

test('template and committed page execute identical margin controllers', () => assert.equal(script(paths[0]), script(paths[1])));
for (const path of paths) {
  for (const lang of ['en', 'zh']) for (const maint of [25, 75, 99.99]) {
    test(`${path} ${lang} 100% initial / ${maint}% maintenance: no borrowing-driven call`, () => {
      const ui = page(path, lang); ui.set({...base, maint});
      assert.equal(ui.get('out-main'), '$10,000.00'); assert.equal(ui.get('out-lev'), '1:1');
      assert.equal(ui.get('out-shares'), '200'); assert.equal(ui.get('out-pos'), '$10,000.00');
      assert.equal(ui.get('out-call'), lang === 'en' ? 'N/A (no borrowing)' : '不适用（无借款）');
      assert.match(ui.get('out-plain'), lang === 'en' ? /single-long model has no borrowing/ : /本单笔做多模型无借款/);
      assert.doesNotMatch(ui.get('out-plain'), /call near \$0\.00/);
      assert.match(ui.copy(), lang === 'en' ? /N\/A \(no borrowing in this single-long model\)/ : /不适用（本单笔做多模型无借款）/);
      assert.doesNotMatch(ui.copy(), /call near \$0\.00/);
    });
  }
  test(`${path} fully paid endpoint handles whole-share rounding and zero shares`, () => {
    const ui = page(path);
    for (const values of [{equity:100,price:3}, {equity:1,price:50}, {equity:12345.67,price:12.34}]) {
      ui.set({...base,...values});
      assert.equal(ui.get('out-main'), money(values.equity));
      assert.equal(ui.get('out-shares'), Math.floor(values.equity / values.price).toLocaleString('en-US'));
      assert.equal(ui.get('out-call'), 'N/A (no borrowing)');
    }
  });
  test(`${path} worked example and 99% borrowing threshold remain byte-for-byte wording`, () => {
    const ui = page(path);
    for (const initial of [50, 99, 99.999999]) {
      ui.set({...base, initial}); const bp = 10000 / (initial/100), call = 50*(1-initial/100)/0.75;
      assert.equal(ui.get('out-main'), money(bp)); assert.equal(ui.get('out-call'), money(call));
      assert.match(ui.get('out-plain'), /a fully-margined long would face a margin call near/);
      assert.match(ui.copy(), /shares · call near \$/);
      assert.doesNotMatch(ui.copy(), /N\/A|no borrowing/);
    }
  });
  test(`${path} initial endpoint does not accept invalid neighboring requirements`, () => {
    const ui = page(path);
    for (const values of [{initial:100.01}, {maint:100}, {maint:101}, {maint:0}, {maint:-1}, {equity:0}, {price:0}, {price:''}, {initial:''}]) {
      ui.set({...base}); ui.copy(); const count = ui.writes.length;
      ui.set(values);
      for (const id of ['out-main','out-lev','out-shares','out-pos','out-call']) assert.equal(ui.get(id), '—');
      ui.copy(); assert.equal(ui.writes.length, count, 'invalid inputs cannot export previous endpoint');
    }
  });
  test(`${path} borrowed -> fully paid -> invalid -> borrowed updates screen and copy`, () => {
    const ui = page(path); ui.set({...base, initial:50}); assert.match(ui.copy(), /call near \$33\.33/);
    ui.set({initial:100}); assert.match(ui.copy(), /N\/A/);
    ui.set({maint:100}); const count=ui.writes.length; ui.copy(); assert.equal(ui.writes.length,count);
    ui.set({maint:25,initial:99}); assert.equal(ui.get('out-call'), '$0.67'); assert.match(ui.copy(), /call near \$0\.67/);
  });
  test(`${path} language change updates endpoint without resetting drafts`, () => {
    const ui = page(path); ui.set(base); const values=ui.values(); ui.language('zh');
    assert.equal(ui.get('out-call'),'不适用（无借款）'); assert.match(ui.get('out-plain'),/本单笔做多模型无借款/); assert.match(ui.copy(),/^保证金/);
    assert.deepEqual(ui.values(),values); ui.language('en');
    assert.equal(ui.get('out-call'),'N/A (no borrowing)'); assert.match(ui.copy(),/^Margin/); assert.deepEqual(ui.values(),values);
  });
  test(`${path} legacy clipboard receives the same no-borrowing disclosure`, () => {
    const ui = page(path,'en',true); ui.set(base); assert.match(ui.copy(), /N\/A \(no borrowing in this single-long model\)/);
    ui.language('zh'); assert.match(ui.copy(), /不适用（本单笔做多模型无借款）/);
  });
  test(`${path} 400 ordinary borrowing fixtures preserve exact arithmetic and copy`, () => {
    const ui = page(path);
    for(let i=1; i<=400; i++) {
      const equity=100+i*13.7, initial=30+(i%70), maint=initial/2, price=1+(i%101)*0.37;
      ui.set({equity,initial,maint,price}); const bp=equity/(initial/100), shares=Math.floor(bp/price), call=price*(1-initial/100)/(1-maint/100);
      assert.equal(ui.get('out-main'),money(bp)); assert.equal(ui.get('out-pos'),money(shares*price));
      assert.equal(ui.get('out-shares'),shares.toLocaleString('en-US')); assert.equal(ui.get('out-call'),money(call));
      assert.ok(ui.copy().includes('shares · call near '+money(call)), 'ordinary copy retains threshold');
    }
  });
}

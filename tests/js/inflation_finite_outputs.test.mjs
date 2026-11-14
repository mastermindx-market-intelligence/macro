import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { test } from 'node:test';
import vm from 'node:vm';

// Execute the unmodified whole calculator controller, including self-check,
// DOMContentLoaded, render, event listeners and copyLine. No copied compute.
// Optional root allows the same suite to discriminate exact baseline bytes.
const root = resolve(process.env.INFLATION_TEST_ROOT || '.');
const paths = ['templates/calculators/inflation.html.j2', 'site/tools/calculators/inflation.html'];
const outputs = ['out-main', 'out-power', 'out-lost', 'out-erosion', 'out-rise'];
const controller = path => {
  const scripts = [...readFileSync(resolve(root, path), 'utf8').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)]
    .map(m => m[1]).filter(s => s.includes('function compute(inp)') && s.includes('inflation self-check'));
  assert.equal(scripts.length, 1);
  return scripts[0];
};
const scripts = paths.map(controller);
assert.equal(scripts[0], scripts[1], 'template/generated controller parity');

function boot(script, transport, options = {}) {
  const errors = [], writes = [], timers = [], nodes = new Map(), ready = [];
  let selected = null, focused = null;
  const pending = []; let legacyCalls = 0;
  function element(id) {
    const listeners = new Map(), classes = new Set();
    return { id, value: '', textContent: '', className: '', hidden: true, style: {},
      setAttribute() {}, focus() { focused = this; },
      classList: {add: x => classes.add(x), remove: x => classes.delete(x), contains: x => classes.has(x)},
      addEventListener(type, fn) { listeners.set(type, fn); },
      fire(type) { assert.ok(listeners.has(type)); return listeners.get(type)(); },
      select() { selected = this; }
    };
  }
  for (const id of ['amount', 'rate', 'years', ...outputs, 'out-plain', 'copy-result', 'copied', 'copy-fail', 'copy-manual', 'copy-manual-text', 'copy-manual-select']) nodes.set(id, element(id));
  const children = [];
  const document = {
    getElementById(id) { assert.ok(nodes.has(id), id); return nodes.get(id); },
    addEventListener(type, fn) { assert.equal(type, 'DOMContentLoaded'); ready.push(fn); },
    createElement(tag) { assert.equal(tag, 'textarea'); return element(tag); },
    body: { appendChild(e) {children.push(e);}, removeChild(e) {assert.equal(children.pop(), e);} },
    execCommand(cmd) {
      legacyCalls++; assert.equal(cmd, 'copy'); assert.ok(selected);
      if(options.legacy === 'throw') throw new Error('copy unavailable');
      if(options.legacy === false) return false;
      writes.push(selected.value); return true;
    }
  };
  const navigator = transport === 'clipboard' ? {clipboard: {writeText(text) {
    writes.push(text);
    if(options.modern === 'throw') throw new Error('write failed');
    if(options.modern === 'reject') return Promise.reject(new Error('write denied'));
    if(options.modern === 'defer') return new Promise((resolve, reject) => pending.push({resolve, reject}));
    return Promise.resolve();
  }}} : {};
  if(options.malformed) navigator.clipboard = {writeText: true};
  vm.runInNewContext(script, {document, navigator, console: {error: (...args) => errors.push(args)}, setTimeout: fn => {timers.push(fn); return fn;}, clearTimeout: fn => {fn.cancelled = true;}});
  assert.equal(ready.length, 1);
  ready[0]();
  assert.deepEqual(errors, [], 'canonical self-check remains silent');
  return {nodes, writes, timers, children, pending,
    get legacyCalls() {return legacyCalls;}, get selected() {return selected;}, get focused() {return focused;},
    input(values) { for (const [id, value] of Object.entries(values)) {nodes.get(id).value = value; nodes.get(id).fire('input');} },
    async copy() {nodes.get('copy-result').fire('click'); await Promise.resolve();},
    text(id) {return nodes.get(id).textContent;},
    resetToast() {while(timers.length) {const fn=timers.shift(); if(!fn.cancelled) fn();}}
  };
}
function valid(ui) {
  for(const id of outputs) {assert.notEqual(ui.text(id), '—', id); assert.doesNotMatch(ui.text(id), /NaN|Infinity|∞/, id);}
  assert.doesNotMatch(ui.text('out-plain'), /NaN|Infinity|∞/);
}
function invalid(ui) {
  for(const id of outputs) {assert.equal(ui.text(id), '—', id); if(id !== 'out-main') assert.equal(ui.nodes.get(id).className, '');}
  assert.ok(ui.text('out-plain').length > 0);
  assert.equal(ui.nodes.get('out-plain').className, 'co-plain');
}
const good = [
  ['canonical inflation', {amount:'1000', rate:'3', years:'10'}, ['$1,343.92','$744.09','$255.91','25.6%','34.4%']],
  ['canonical zero', {amount:'10000', rate:'0', years:'20'}, ['$10,000.00','$10,000.00','$0.00','0.0%','0.0%']],
  ['deflation', {amount:'1000', rate:'-50', years:'2'}, ['$250.00','$4,000.00','-$3,000.00','-300.0%','-75.0%']],
  ['commas and whitespace', {amount:' 1,000 ', rate:'3', years:'10'}, ['$1,343.92','$744.09','$255.91','25.6%','34.4%']],
  ['near future cost boundary', {amount:'4e307', rate:'100', years:'2'}],
  ['near purchasing power boundary', {amount:'4e307', rate:'-50', years:'2'}],
  ['large finite percentage', {amount:'1e-300', rate:'1e306', years:'1'}],
  ['subnormal positive amount', {amount:'5e-324', rate:'0', years:'1'}]
];
const overflow = [
  ['future cost', {amount:'1e308', rate:'100', years:'2'}],
  ['purchasing power and loss', {amount:'1e308', rate:'-50', years:'2'}],
  ['erosion multiplication only', {amount:'1e-308', rate:'-99', years:'154'}],
  ['reciprocal erosion', {amount:'1e-308', rate:'-99', years:'155'}],
  ['price rise only', {amount:'1e-300', rate:'1e308', years:'1.005'}]
];
for (const [index, path] of paths.entries()) for(const transport of ['clipboard', 'fallback']) {
  const name = `${path} / ${transport}`;
  for(const [label, inputs, expected] of good) test(`${name} / ${label}`, async () => {
    const ui = boot(scripts[index], transport); ui.input(inputs); valid(ui);
    if(expected) assert.deepEqual(outputs.map(id=>ui.text(id)), expected.map(x=>x.replace('-$', '$-')));
    if(label === 'deflation') {assert.equal(ui.nodes.get('out-erosion').className, 'pos'); assert.match(ui.text('out-plain'), /prices falling/);}
    await ui.copy(); assert.equal(ui.writes.length, 1); assert.match(ui.writes[0], /^Inflation: future cost .* · purchasing power .* · .* erosion — mastermind-x\.com$/);
    assert.doesNotMatch(ui.writes[0], /NaN|Infinity|∞/); assert.equal(ui.children.length, 0);
    assert.equal(ui.nodes.get('copied').classList.contains('show'), true); ui.resetToast(); assert.equal(ui.nodes.get('copied').classList.contains('show'), false);
  });
  for(const [label, inputs] of overflow) test(`${name} / reject ${label}`, async () => {
    // Fixture preconditions: finite caller inputs and a finite positive factor.
    // This is not the implementation oracle: controller output and events below are.
    for(const v of Object.values(inputs)) assert.ok(Number.isFinite(Number(v)));
    const factor = Math.pow(1 + Number(inputs.rate)/100, Number(inputs.years));
    assert.ok(Number.isFinite(factor) && factor > 0);
    const ui = boot(scripts[index], transport); ui.input(inputs);
    await ui.copy(); assert.equal(ui.writes.length, 0, 'overflow must not reach either clipboard boundary');
    invalid(ui); assert.match(ui.text('out-plain'), /too extreme/); assert.equal(ui.timers.length, 0);
  });
  for(const [label, inputs] of [['empty', {}], ['invalid factor', {amount:'1000', rate:'100', years:'2000'}]]) test(`${name} / ${label}`, async () => {
    const ui = boot(scripts[index], transport); ui.input(inputs); invalid(ui); await ui.copy(); assert.equal(ui.writes.length, 0);
  });
  test(`${name} / valid → overflow → withheld copy → correction`, async () => {
    const ui = boot(scripts[index], transport); ui.input(good[0][1]); valid(ui); await ui.copy(); assert.equal(ui.writes.length, 1); ui.resetToast();
    for(const [, inputs] of overflow) {
      ui.input(inputs); invalid(ui); await ui.copy(); assert.equal(ui.writes.length, 1); assert.equal(ui.nodes.get('copied').classList.contains('show'), false);
    }
    ui.input(good[2][1]); valid(ui); await ui.copy(); assert.equal(ui.writes.length, 2); assert.match(ui.writes[1], /future cost \$250\.00/); assert.match(ui.writes[1], /-300\.0% erosion/);
  });
}

// Truthful clipboard feedback: scripted API boundaries, not an OS clipboard.
const silent = ui => {
  assert.equal(ui.nodes.get('copied').classList.contains('show'), false, 'no success toast');
  assert.equal(ui.nodes.get('copy-fail').hidden, true, 'no stale failure');
  assert.equal(ui.nodes.get('copy-manual').hidden, true, 'no stale manual text');
  assert.equal(ui.nodes.get('copy-manual-text').value, '');
};
const failed = ui => {
  assert.equal(ui.nodes.get('copied').classList.contains('show'), false, 'failed write cannot claim success');
  assert.equal(ui.nodes.get('copy-fail').hidden, false);
  assert.equal(ui.nodes.get('copy-manual').hidden, false);
  assert.match(ui.nodes.get('copy-manual-text').value, /^Inflation: future cost \$1,343\.92/);
};
const flush = async () => {await Promise.resolve(); await Promise.resolve();};
for(const [index, path] of paths.entries()) {
  for(const modern of ['reject', 'throw']) test(`${path} / modern ${modern} offers exact manual text without retry`, async () => {
    const ui=boot(scripts[index], 'clipboard', {modern}); ui.input(good[0][1]); await ui.copy();
    failed(ui); assert.equal(ui.nodes.get('copy-manual-text').value, ui.writes[0]);
    assert.equal(ui.legacyCalls, 0); assert.equal(ui.children.length, 0);
    assert.equal(ui.timers.length, 0, 'failure stays available without a success timer');
    ui.nodes.get('copy-manual-select').fire('click');
    assert.equal(ui.selected, ui.nodes.get('copy-manual-text'));
    assert.equal(ui.focused, ui.nodes.get('copy-manual-text'));
    assert.equal(ui.nodes.get('amount').value, '1000');
    assert.equal(ui.nodes.get('rate').value, '3');
    assert.equal(ui.nodes.get('years').value, '10');
  });
  for(const legacy of [false, 'throw']) test(`${path} / legacy ${legacy} reports failure and removes temporary field`, async () => {
    const ui=boot(scripts[index], 'fallback', {legacy}); ui.input(good[0][1]); await ui.copy();
    failed(ui); assert.equal(ui.legacyCalls, 1); assert.equal(ui.writes.length, 0);
    assert.equal(ui.children.length, 0); assert.equal(ui.timers.length, 0);
  });
  test(`${path} / non-callable Clipboard API uses legacy once`, async () => {
    const ui=boot(scripts[index], 'fallback', {malformed:true}); ui.input(good[0][1]); await ui.copy();
    assert.equal(ui.legacyCalls,1); assert.equal(ui.writes.length,1);
    assert.equal(ui.nodes.get('copied').classList.contains('show'),true);
  });
  for(const mode of ['resolve','reject']) for(const field of ['amount','rate','years']) {
    test(`${path} / pending ${mode} cannot outlive ${field} edit`, async () => {
      const ui=boot(scripts[index],'clipboard',{modern:'defer'}); ui.input(good[0][1]); await ui.copy();
      ui.input({[field]: field==='amount'?'2000':field==='rate'?'4':'20'});
      ui.pending[0][mode](new Error('late completion')); await flush(); silent(ui);
      assert.equal(ui.legacyCalls,0); assert.equal(ui.writes.length,1);
      assert.equal(ui.timers.length,0);
    });
    test(`${path} / pending ${mode} cannot outlive invalid ${field}`, async () => {
      const ui=boot(scripts[index],'clipboard',{modern:'defer'}); ui.input(good[0][1]); await ui.copy();
      ui.input({[field]:''}); invalid(ui);
      ui.pending[0][mode](new Error('late completion')); await flush(); silent(ui);
      await ui.copy(); assert.equal(ui.writes.length,1); assert.equal(ui.pending.length,1);
    });
  }
  for(const modern of ['reject', undefined]) for(const field of ['amount','rate','years']) {
    test(`${path} / completed ${modern || 'success'} feedback clears on ${field} edit`, async () => {
      const ui=boot(scripts[index],'clipboard',{modern}); ui.input(good[0][1]); await ui.copy();
      ui.input({[field]:''}); silent(ui); ui.resetToast(); silent(ui);
    });
  }
  test(`${path} / older failure cannot replace newer successful copy`, async () => {
    const ui=boot(scripts[index],'clipboard',{modern:'defer'}); ui.input(good[0][1]);
    await ui.copy(); await ui.copy();
    ui.pending[1].resolve(); await flush();
    ui.pending[0].reject(new Error('old failed')); await flush();
    assert.equal(ui.nodes.get('copied').classList.contains('show'),true);
    assert.equal(ui.nodes.get('copy-manual').hidden,true);
    assert.equal(ui.nodes.get('copy-fail').hidden,true); assert.equal(ui.legacyCalls,0);
  });
  test(`${path} / older success cannot replace newer failure`, async () => {
    const ui=boot(scripts[index],'clipboard',{modern:'defer'}); ui.input(good[0][1]);
    await ui.copy(); await ui.copy();
    ui.pending[1].reject(new Error('new failed')); await flush(); failed(ui);
    ui.pending[0].resolve(); await flush(); failed(ui); assert.equal(ui.timers.length,0);
  });
  test(`${path} / failure recovery clears manual text before next successful attempt`, async () => {
    const ui=boot(scripts[index],'clipboard',{modern:'defer'}); ui.input(good[0][1]);
    await ui.copy(); ui.pending[0].reject(new Error('denied')); await flush(); failed(ui);
    await ui.copy(); silent(ui); ui.pending[1].resolve(); await flush();
    assert.equal(ui.nodes.get('copied').classList.contains('show'),true);
    assert.equal(ui.nodes.get('copy-manual').hidden,true); assert.equal(ui.nodes.get('copy-manual-text').value,'');
  });
  test(`${path} / an old timer cannot hide the current success`, async () => {
    const ui=boot(scripts[index],'clipboard'); ui.input(good[0][1]); await ui.copy();
    const oldTimer=ui.timers[0]; await ui.copy(); oldTimer();
    assert.equal(ui.nodes.get('copied').classList.contains('show'),true);
    ui.resetToast(); assert.equal(ui.nodes.get('copied').classList.contains('show'),false);
  });
  test(`${path} / hidden manual-select button cannot select stale output`, () => {
    const ui=boot(scripts[index],'clipboard'); ui.nodes.get('copy-manual-select').fire('click');
    assert.equal(ui.selected,null); assert.equal(ui.focused,null);
  });
}

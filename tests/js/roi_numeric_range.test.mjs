/**
 * ROI finite-output regression, derived from the reviewed #10934 candidate.
 * Runs the whole actual inline controller over both template and committed page.
 * DOM/clipboard are recording fixtures, not browser or native-copy proof.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import nativeTest from 'node:test';
const ROOT = process.env.ROI_TEST_ROOT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const paths = ['templates/calculators/roi.html.j2', 'site/tools/calculators/roi.html'];
function extract(file) {
  const text = fs.readFileSync(path.join(ROOT, file), 'utf8');
  const scripts = [...text.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(match => match[1]).filter(script => script.includes('function compute(inp)') && script.includes('roi self-check'));
  assert.equal(scripts.length, 1, 'Exactly one ROI controller must exist in ' + file);
  return scripts[0];
}
const scripts = paths.map(extract);
nativeTest('ROI template and committed page controller parity', () => assert.equal(scripts[0], scripts[1]));
for (const [surface, source] of scripts.entries()) {
  const cases = [];
  const test = (name, run) => cases.push([name, run]);
function mount(script = source) {
  const elements = {}, listeners = {}, copies = [], errors = [];
  let lang = 'en';
  for (const id of ['cost','value','years','out-main','out-plain','out-profit','out-roi','out-annual','copy-result','copied']) {
    elements[id] = {value:'', textContent:'', className:'', handlers:{},
      classList:{add(){},remove(){}}, addEventListener(type, fn){this.handlers[type]=fn;}};
  }
  const document = {
    documentElement:{getAttribute(key){assert.equal(key,'data-lang');return lang;}},
    getElementById(id){assert.ok(elements[id],id);return elements[id];},
    addEventListener(type, fn){listeners[type]=fn;},
  };
  const context = {document, navigator:{clipboard:{writeText(text){copies.push(text);return Promise.resolve();}}},
    console:{error(...args){errors.push(args);}}, setTimeout(){}};
  const marker = '  // ── §6 self-check:';
  assert.equal(script.split(marker).length, 2);
  vm.runInNewContext(script.replace(marker, '  globalThis.compute = compute;\n'+marker), context, {timeout:1000});
  listeners.DOMContentLoaded();
  assert.deepEqual(errors, [], 'Canonical worked-example self-check must remain clean');
  return {compute:context.compute, elements, copies,
    input(C,V,n=''){elements.cost.value=String(C);elements.value.value=String(V);elements.years.value=String(n);elements.cost.handlers.input();},
    copy(){elements['copy-result'].handlers.click();return copies.at(-1);},
    language(value){lang=value; if(listeners.langchange) listeners.langchange();},
    text(){return ['out-main','out-plain','out-profit','out-roi','out-annual'].map(id=>elements[id].textContent).join(' | ');},
  };
}
function near(actual, expected) {assert.ok(Math.abs(actual-expected)<=1e-12*Math.max(1,Math.abs(expected)),`${actual} != ${expected}`);}

test('canonical example and actual rendered/copy values',()=>{
  const w=mount();w.input(1000,1500,2);
  assert.equal(w.elements['out-main'].textContent,'+50.0%');assert.equal(w.elements['out-profit'].textContent,'$500.00');
  assert.equal(w.elements['out-annual'].textContent,'+22.5%');assert.match(w.copy(),/\+22\.5%\/yr/);
});
test('annual overflow preserves finite ROI and profit, with explicit UI/copy uncertainty',()=>{
  const w=mount();w.input(1000,1100,.0001);const r=w.compute({C:1000,V:1100,n:.0001});
  assert.equal(r.ok,true);assert.equal(r.netProfit,100);assert.equal(r.roiPct,10);assert.equal(r.annualPct,null);assert.equal(r.annualOutOfRange,true);
  assert.equal(w.elements['out-main'].textContent,'+10.0%');assert.equal(w.elements['out-profit'].textContent,'$100.00');
  assert.equal(w.elements['out-annual'].textContent,'Out of range');assert.match(w.elements['out-plain'].textContent,/unavailable/);
  assert.match(w.copy(),/annualized unavailable/);assert.doesNotMatch(w.text()+w.copy(),/NaN|Infinity|∞/);
});
test('neighboring short hold stays finite',()=>{
  const w=mount();w.input(1000,1100,.001);const r=w.compute({C:1000,V:1100,n:.001});
  assert.ok(Number.isFinite(r.annualPct));assert.equal(r.annualOutOfRange,false);assert.doesNotMatch(w.text()+w.copy(),/NaN|Infinity|∞|unavailable|Out of range/);
});
test('large finite ratio avoids multiplication-before-division overflow',()=>{
  const w=mount();const r=w.compute({C:1e308,V:1.5e308,n:2});assert.equal(r.ok,true);near(r.roiPct,50);near(r.netProfit,5e307);near(r.annualPct,22.474487139158896);
  w.input(1e308,1.5e308,2);assert.equal(w.elements['out-main'].textContent,'+50.0%');assert.doesNotMatch(w.text()+w.copy(),/NaN|Infinity|∞/);
});
test('unrepresentable profit rejects coherently and cannot copy',()=>{
  const w=mount();w.input(1e308,-1e308,2);assert.equal(w.compute({C:1e308,V:-1e308,n:2}).ok,false);
  for(const id of ['out-main','out-profit','out-roi','out-annual'])assert.equal(w.elements[id].textContent,'—');
  assert.match(w.elements['out-plain'].textContent,/numeric range/);w.copy();assert.equal(w.copies.length,0);
});
test('unrepresentable ROI rejects coherently',()=>{
  const w=mount();w.input(1e-300,1e308,2);assert.equal(w.compute({C:1e-300,V:1e308,n:2}).ok,false);assert.doesNotMatch(w.text(),/NaN|Infinity|∞/);
});
test('blank invalid clearing and recovery retire prior copy',()=>{
  const w=mount();w.input(1000,1500,2);w.input('',1500,2);assert.equal(w.elements['out-main'].textContent,'—');w.copy();assert.equal(w.copies.length,0);
  w.input(1000,1500,2);assert.equal(w.elements['out-main'].textContent,'+50.0%');assert.match(w.copy(),/\+50\.0%/);
});
test('negative and zero final values retain existing semantics',()=>{
  const w=mount();for(const V of [-1000,0]){const r=w.compute({C:1000,V,n:2});assert.equal(r.ok,true);assert.equal(r.roiPct,V===0?-100:-200);assert.equal(r.annualPct,null);assert.equal(r.annualOutOfRange,false);}
});
test('omitted, zero and negative years remain unannualized',()=>{
  const w=mount();for(const n of [undefined,NaN,0,-1]){const r=w.compute({C:1000,V:1500,n});assert.equal(r.ok,true);assert.equal(r.annualPct,null);assert.equal(r.annualOutOfRange,false);}
});
test('ordinary sub-year gain remains unchanged',()=>{
  const w=mount();const r=w.compute({C:1000,V:1100,n:.5});near(r.annualPct,21);assert.equal(r.shortHold,true);
});
test('tiny-period loss remains finite minus100 annual, not a range error',()=>{
  const w=mount();const r=w.compute({C:1000,V:900,n:.0001});assert.equal(r.annualPct,-100);assert.equal(r.annualOutOfRange,false);
});
test('new range messages track EN/ZH without altering drafts',()=>{
  const w=mount();w.input(1000,1100,.0001);w.language('zh');assert.equal(w.elements['out-annual'].textContent,'超出数值范围');
  assert.match(w.elements['out-plain'].textContent,/年化回报超出/);assert.match(w.copy(),/年化回报无法显示/);
  assert.deepEqual(['cost','value','years'].map(id=>w.elements[id].value),['1000','1100','0.0001']);
  w.language('en');assert.equal(w.elements['out-annual'].textContent,'Out of range');assert.match(w.copy(),/annualized unavailable/);
});
test('new invalid-result message is bilingual and stays uncopiable',()=>{
  const w=mount();w.input(1e308,-1e308,2);w.language('zh');assert.equal(w.elements['out-plain'].textContent,'结果超出支持的数值范围。');w.copy();assert.equal(w.copies.length,0);
});
test('range state clears after recovering ordinary values',()=>{
  const w=mount();w.input(1000,1100,.0001);w.input(1000,1500,2);assert.equal(w.elements['out-annual'].textContent,'+22.5%');assert.doesNotMatch(w.text()+w.copy(),/unavailable|Out of range/);
});
test('numeric closure over 560 boundary fixtures',()=>{
  const w=mount();let count=0;
  for(const C of [1e-300,1e-10,1,1000,1e100,1e200,1e308])for(const V of [-1e308,-1e100,-1,0,1,1000,1e100,1.5e308])for(const n of [-1,0,.0001,.001,.5,1,2,1000,Infinity,NaN]){
    const r=w.compute({C,V,n});for(const value of Object.values(r))if(typeof value==='number')assert.ok(Number.isFinite(value),JSON.stringify({C,V,n,r}));count++;
  }assert.equal(count,560);
});
test('unchanged investment has exact zero annual return even for tiny positive years',()=>{
  const w=mount();for(const C of [1,1000,1e308]){const r=w.compute({C,V:C,n:1e-309});assert.equal(r.annualPct,0);assert.equal(r.annualOutOfRange,false);}
  w.input(1000,1000,1e-309);assert.equal(w.elements['out-annual'].textContent,'+0.00%');assert.match(w.copy(),/\+0\.00%\/yr/);
});

  for (const [name, run] of cases) {
    // Node's native test runner owns reporting and failures.
    nativeTest(paths[surface] + ': ' + name, run);
  }
}

/**
 * Drawdown source selection: run each complete native controller over a recording
 * DOM/clipboard fixture. This is executable wiring proof, not real-browser proof.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import test from 'node:test';

const ROOT = process.env.DRAWDOWN_TEST_ROOT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const files = ['templates/calculators/drawdown_recovery.html.j2', 'site/tools/calculators/drawdown-recovery.html'];
function extract(file) {
  const content = fs.readFileSync(path.join(ROOT, file), 'utf8');
  const scripts = [...content.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(m => m[1]).filter(s => s.includes('drawdown self-check'));
  assert.equal(scripts.length, 1, file);
  return scripts[0];
}
const scripts = files.map(extract);
test('template and committed controller stay identical', () => assert.equal(scripts[0], scripts[1]));

function mount(source) {
  const ids = ['dd-pct','peak','current','ret-rate','out-main','out-plain','out-dd','out-years','out-loss','copy-result','copied'];
  const elements = {}, listeners = {}, copies = [], errors = [];
  let lang = 'en';
  for (const id of ids) elements[id] = {value:'',textContent:'',className:'',handlers:{},
    classList:{add(){},remove(){}},addEventListener(name, fn){this.handlers[name]=fn;}};
  const document = {
    documentElement:{getAttribute(key){assert.equal(key,'data-lang');return lang;}},
    getElementById(id){assert.ok(elements[id],id);return elements[id];},
    addEventListener(name,fn){listeners[name]=fn;},
  };
  const context = {document,navigator:{clipboard:{writeText(text){copies.push(text);return Promise.resolve();}}},
    console:{error(...args){errors.push(args);}},setTimeout(){}};
  const marker = '  // ── §6 self-check';
  assert.equal(source.split(marker).length,2);
  vm.runInNewContext(source.replace(marker,'  globalThis.compute=compute;\n'+marker),context,{timeout:1000});
  listeners.DOMContentLoaded();
  assert.deepEqual(errors,[], 'Worked examples must remain clean');
  return {elements,copies,compute:context.compute,
    input(d='',p='',c='',g=''){for(const [id,value] of Object.entries({'dd-pct':d,peak:p,current:c,'ret-rate':g}))elements[id].value=String(value);elements['dd-pct'].handlers.input();},
    copy(){elements['copy-result'].handlers.click();return copies.at(-1);},
    language(value){lang=value;if(listeners.langchange)listeners.langchange();},
  };
}

for (const [index, source] of scripts.entries()) {
  const check = (name, fn) => test(files[index]+': '+name, () => fn(mount(source)));
  for (const [name,peak,current] of [
    ['negative current','100000','-10000'],['unreadable current','100000','abc'],
    ['missing current','100000',''],['missing peak','','50000'],
    ['zero peak','0','50000'],['negative peak','-100000','50000'],
    ['unreadable peak','abc','50000'],['two unreadable balances','abc','def'],
    ['nonfinite current','100000','Infinity'],['nonfinite peak','Infinity','50000'],
  ]) check(name+' retains percentage math with truthful screen and copy', w => {
    w.input(20,peak,current,10);
    assert.equal(w.elements['out-main'].textContent,'+25.0%');
    assert.equal(w.elements['out-dd'].textContent,'20.0% (from entered drawdown %)');
    assert.equal(w.elements['out-loss'].textContent,'—');
    assert.equal(w.elements['out-years'].textContent,'2.3 yr at 10.0% annual');
    assert.match(w.elements['out-plain'].textContent,/Peak\/current values are incomplete or invalid/);
    const copy=w.copy();assert.match(copy,/from entered drawdown %/);assert.match(copy,/incomplete or invalid/);assert.doesNotMatch(copy,/from peak\/current/);
  });
  check('percentage-only mode is explicit without an ignored-balance warning', w => {
    w.input(20,'','',10);
    assert.equal(w.elements['out-dd'].textContent,'20.0% (from entered drawdown %)');
    assert.doesNotMatch(w.elements['out-plain'].textContent,/incomplete|invalid/);
    assert.match(w.copy(),/from entered drawdown %/);assert.doesNotMatch(w.copy(),/incomplete|invalid/);
  });
  check('whitespace-only balances are absent, not ignored entered values', w => {
    w.input(20,'  ','\t',10);assert.doesNotMatch(w.elements['out-plain'].textContent,/incomplete|invalid/);
    assert.match(w.copy(),/from entered drawdown %/);
  });
  check('valid balances override an inconsistent percentage with shared provenance', w => {
    w.input(20,'100,000','50,000',10);
    assert.equal(w.elements['out-main'].textContent,'+100.0%');assert.equal(w.elements['out-dd'].textContent,'50.0% (from peak/current)');
    assert.equal(w.elements['out-loss'].textContent,'$50,000 from peak');assert.equal(w.elements['out-years'].textContent,'7.3 yr at 10.0% annual');
    assert.match(w.copy(),/from peak\/current/);assert.doesNotMatch(w.copy(),/incomplete|invalid|from entered/);
  });
  check('valid balances still work without a percentage', w => {
    w.input('','100000','50000');assert.equal(w.elements['out-main'].textContent,'+100.0%');assert.match(w.copy(),/from peak\/current/);
  });
  for (const [name,peak,current] of [['total loss',100000,0],['above peak',100000,100001],['no drawdown',100000,100000]]) {
    check(name+' retains refusal, clears previous result and cannot copy', w => {
      w.input(20,'','',10);w.input(20,peak,current,10);
      for(const id of ['out-main','out-dd','out-years','out-loss'])assert.equal(w.elements[id].textContent,'—');
      w.copy();assert.equal(w.copies.length,0);
    });
  }
  check('unusable pair without a valid percentage is still refused', w => {
    w.input('',100000,'abc',10);assert.equal(w.elements['out-main'].textContent,'—');w.copy();assert.equal(w.copies.length,0);
  });
  check('fallback, valid pair, percent-only and invalid transitions do not leak provenance', w => {
    w.input(20,100000,-1,10);assert.match(w.copy(),/incomplete or invalid/);
    w.input(20,100000,50000,10);assert.doesNotMatch(w.copy(),/incomplete|invalid|from entered/);
    w.input(20,'','',10);assert.doesNotMatch(w.copy(),/incomplete|invalid|from peak/);
    w.input('','','',10);const count=w.copies.length;w.copy();assert.equal(w.copies.length,count);
  });
  check('new source and fallback disclosure follow live EN/ZH changes without changing drafts', w => {
    w.input(20,100000,-10000,10);w.language('zh');
    assert.equal(w.elements['out-dd'].textContent,'20.0%（使用输入的回撤百分比）');
    assert.match(w.elements['out-plain'].textContent,/峰值\/当前值不完整或无效/);assert.match(w.copy(),/使用输入的回撤百分比/);
    assert.deepEqual(['dd-pct','peak','current','ret-rate'].map(id=>w.elements[id].value),['20','100000','-10000','10']);
    w.input(20,100000,50000,10);assert.equal(w.elements['out-dd'].textContent,'50.0%（由峰值/当前值计算）');assert.match(w.copy(),/由峰值\/当前值计算/);
    w.language('en');assert.match(w.copy(),/from peak\/current/);assert.doesNotMatch(w.copy(),/不完整|invalid/);
  });
  check('600 ordinary arithmetic and source-selection cases', w => {
    let count=0;
    for(const peak of [100,1000,100000,1e6,1e9])for(const fraction of [.1,.25,.5,.75,.9])for(const d of [5,20,50,80])for(const g of [NaN,1,5,10,25,100]) {
      const current=peak*fraction;const r=w.compute({ddPct:d,peak,current,g,balanceEntered:true});
      assert.equal(r.ok,true);assert.equal(r.fromPeakCurrent,true);assert.equal(r.percentFallback,false);
      const expectedD=(peak-current)/peak*100;assert.equal(r.d,expectedD);assert.equal(r.reqGain,100*expectedD/(100-expectedD));
      assert.equal(r.dollarLoss,peak-current);if(Number.isFinite(g))assert.equal(r.years,Math.log(100/(100-expectedD))/Math.log(1+g/100));count++;
    } assert.equal(count,600);
  });
}

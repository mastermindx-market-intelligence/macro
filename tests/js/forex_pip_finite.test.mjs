/** Execute both complete Forex Pip controllers, with deterministic DOM/copy boundaries.
 * node --test tests/js/forex_pip_finite.test.mjs
 * FOREX_PIP_ROOT=/path/to/source node --test tests/js/forex_pip_finite.test.mjs
 * These are source tests, not browser or native OS clipboard acceptance.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import vm from 'node:vm';

const ROOT=process.env.FOREX_PIP_ROOT || join(dirname(fileURLToPath(import.meta.url)),'../..');
const paths=['templates/calculators/forex_pip_value.html.j2','site/tools/calculators/forex-pip-value.html'];
function controller(path){
  const blocks=[...readFileSync(join(ROOT,path),'utf8').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)];
  const matches=blocks.filter(x=>x[1].includes('var pipQuote = p * U;'));
  assert.equal(matches.length,1);return matches[0][1];
}
function load(path,lang='en'){
  const listeners=new Map(), elems=new Map(), errors=[], writes=[], timers=[];
  function el(id){
    if(elems.has(id))return elems.get(id);
    const events={},classes=new Set();
    const e={value:'',textContent:'',className:'',events,addEventListener(k,f){events[k]=f;},
      classList:{add(k){classes.add(k);},remove(k){classes.delete(k);},toggle(k,on){on?classes.add(k):classes.delete(k);}},
      setAttribute(){},getAttribute(k){return k==='data-v'?id:null;},closest(){return e;}};
    elems.set(id,e);return e;
  }
  const buttons=[el('0.0001'),el('0.01')],seg=el('seg');seg.querySelectorAll=()=>buttons;
  const document={getElementById:el,querySelector:()=>seg,documentElement:{getAttribute:()=>lang},
    addEventListener(k,f){if(!listeners.has(k))listeners.set(k,[]);listeners.get(k).push(f);}};
  const context=vm.createContext({document,console:{error(...a){errors.push(a);}},
    navigator:{clipboard:{writeText(s){writes.push(s);return Promise.resolve();}}},
    setTimeout(f){timers.push(f);return timers.length;}});
  const src=controller(path);vm.runInContext(src,context);
  for(const f of listeners.get('DOMContentLoaded')||[])f();
  // Obtain the same pure function separately without changing the controller run.
  const start=src.indexOf('  function compute(inp){'),end=src.indexOf('\n  // ── self-check',start);
  assert.ok(start>=0&&end>start);const pure=vm.runInNewContext(src.slice(start,end)+';compute');
  return {el,writes,errors,pure,set(U,q,p='0.0001'){
    el('units').value=String(U);el('qrate').value=String(q);
    seg.events.click({target:el(p)});
  },input(id,value){el(id).value=String(value);el(id).events.input();},
  copy(){el('copy-result').events.click();},
  language(v){lang=v;for(const f of listeners.get('langchange')||[])f();},
  outputs(){return ['out-main','out-quote','out-account','out-mini'].map(k=>el(k).textContent);}};
}
const normal=[
  [100000,1,'0.0001',['$10.00','10.00','$10.00','$1.00']],
  [10000,1,'0.0001',['$1.00','1.00','$1.00','$1.00']],
  [1000,1,'0.0001',['$0.10','0.10','$0.10','$1.00']],
  [100000,1/150,'0.01',['$6.67','1,000.00','$6.67','$0.67']],
  [100000,0.92,'0.0001',['$9.20','10.00','$9.20','$0.92']]
];
for(const path of paths){
  test(`${path}: worked examples and conversion controls`,()=>{
    const h=load(path);assert.deepEqual(h.errors,[]);
    for(const [U,q,p,want]of normal){h.set(U,q,p);assert.deepEqual(h.outputs(),want);h.copy();
      const s=h.writes.at(-1);assert.ok(s.includes(want[0]+' per pip (account)'));assert.ok(s.includes(want[3]+' per 0.1 lot'));}
  });
  for(const [name,U,q,p]of [['main',100000,1e308,'0.0001'],['mini-only',1,1e308,'0.01']]){
    test(`${path}: ${name} overflow clears all outputs and refuses copy`,()=>{
      const h=load(path);h.set(100000,1);h.copy();const before=h.writes.length;
      h.set(U,q,p);assert.deepEqual(h.outputs(),['—','—','—','—']);
      assert.match(h.el('out-plain').textContent,/outside the supported numeric range/);
      h.copy();assert.equal(h.writes.length,before);
      h.set(100000,1);assert.deepEqual(h.outputs(),normal[0][3]);h.copy();assert.equal(h.writes.length,before+1);
    });
  }
  test(`${path}: overflow on first entry does not publish a result`,()=>{
    const h=load(path);h.set(1,1e308,'0.01');h.copy();assert.deepEqual(h.outputs(),['—','—','—','—']);assert.equal(h.writes.length,0);
  });
  test(`${path}: mini-lot guard includes a finite headline counterexample`,()=>{
    const h=load(path);assert.equal(Number.isFinite(0.01*1*1e308),true);
    assert.equal(Number.isFinite(0.01*10000*1e308),false);
    assert.equal(h.pure({U:1,p:0.01,q:1e308}).ok,false);
  });
  test(`${path}: both pip modes recover as reference overflow changes`,()=>{
    const h=load(path);h.set(1,1e308,'0.01');assert.equal(h.el('out-main').textContent,'—');
    h.set(1,1e308,'0.0001');assert.notEqual(h.el('out-main').textContent,'—');h.copy();assert.equal(h.writes.length,1);
    assert.doesNotMatch(h.writes[0],/Infinity|NaN|∞/);h.set(1,1e308,'0.01');h.copy();assert.equal(h.writes.length,1);
  });
  test(`${path}: all derived results and positive finite inputs are guarded`,()=>{
    const h=load(path);
    for(const input of [{U:2,p:Number.MAX_VALUE,q:1},{U:1,p:1,q:Infinity},{U:Infinity,p:1,q:1},{U:1,p:Infinity,q:1}]){
      assert.equal(h.pure(input).ok,false,JSON.stringify(input));}
  });
  test(`${path}: invalid inputs clear output and correction recovers`,()=>{
    const h=load(path);h.set(100000,1);h.copy();let n=h.writes.length;
    for(const [id,value]of [['units',''],['units','-1'],['units','0'],['units','1e309'],['qrate',''],['qrate','0'],['qrate','-1'],['qrate','invalid'],['qrate','1e309']]){
      h.set(100000,1);h.input(id,value);assert.deepEqual(h.outputs(),['—','—','—','—']);h.copy();assert.equal(h.writes.length,n);
      h.input(id,id==='units'?'100000':'1');assert.deepEqual(h.outputs(),normal[0][3]);}
  });
  test(`${path}: EN/ZH overflow message follows language without changing inputs`,()=>{
    const h=load(path,'zh');h.set(1,1e308,'0.01');assert.match(h.el('out-plain').textContent,/超出可计算范围/);
    h.language('en');assert.match(h.el('out-plain').textContent,/outside the supported numeric range/);
    h.language('zh');assert.match(h.el('out-plain').textContent,/超出可计算范围/);
    assert.equal(h.el('units').value,'1');assert.equal(h.el('qrate').value,'1e+308');h.copy();assert.equal(h.writes.length,0);
  });
  test(`${path}: 640 finite combinations preserve the existing formulas exactly`,()=>{
    const h=load(path);let n=0;
    for(const U of [0.01,1,10,1000,10000,100000,1e10,1e100])for(const p of [0.0001,0.01])
      for(const q of [0.01,0.1,0.5,0.92,1,1.1,2,100])for(const scale of [0.001,0.1,1,10,100]){
        const value=q*scale,r=h.pure({U,p,q:value});assert.equal(r.ok,true);
        assert.equal(r.pipQuote,p*U);assert.equal(r.pipAccount,p*U*value);assert.equal(r.perMiniLot,p*10000*value);n++;}
    assert.equal(n,640);
  });
}
test('template and committed page contain identical controllers',()=>assert.equal(controller(paths[0]),controller(paths[1])));
